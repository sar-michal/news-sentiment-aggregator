import logging

from celery.signals import worker_process_init
from pydantic import ValidationError

from app.schemas.article import ArticleData
from app.services.es_client import ElasticClient
from app.services.gdelt import GdeltFetcher
from app.services.nlp import NLPProcessor
from app.services.scraper import NewsScraper
from app.workers.celery_app import celery

logger = logging.getLogger(__name__)

gdelt_fetcher = None
scraper = None
es_client = None
nlp_processor = None


@worker_process_init.connect
def init_worker_services(**kwargs):
    """
    Celery Signal: Runs strictly once when the worker process boots up.
    """
    global gdelt_fetcher, scraper, es_client, nlp_processor

    # Suppress unneeded logs
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("elastic_transport.transport").setLevel(logging.WARNING)

    logger.info(
        "Initializing global worker services, ML models, and connection pools..."
    )
    gdelt_fetcher = GdeltFetcher()
    scraper = NewsScraper()
    es_client = ElasticClient()

    nlp_processor = NLPProcessor()

    es_client.create_index()


@celery.task(bind=True, max_retries=2)
def trigger_gdelt_fetch(self):
    """Producer: Fetches the latest GDELT articles and queues respective scraping tasks."""
    logger.info("Starting GDELT fetch...")
    try:
        articles = gdelt_fetcher.fetch_latest_news(max_records=50)
    except ConnectionError as e:
        if self.request.retries < self.max_retries:
            # 90s, 180s...
            delay = 90 * (2**self.request.retries)

            logger.warning(
                f"Retrying in {delay}s... (Attempt {self.request.retries + 1}/{self.max_retries})"
            )
            raise self.retry(exc=e, countdown=delay)

        logger.error(
            "GDELT fetch aborted: Maximum retries reached. Yielding until next cycle."
        )
        return "Failed: GDELT retry limit reached"

    if not articles:
        logger.info("No articles fetched this cycle.")
        return "No articles queued."

    for article in articles:
        article_dict = article.model_dump(mode="json")
        process_article.delay(article_dict)

    return f"Queued {len(articles)} articles for processing."


@celery.task(
    bind=True,
    max_retries=2,
    autoretry_for=(ConnectionError,),
    retry_backoff=30,
)
def process_article(self, article_dict: dict):
    """
    Consumer: Downloads HTML and extracts article text, indexes base document,
    and executes Aspect-Based Sentiment Analysis pipeline
    """
    try:
        article_data = ArticleData(**article_dict)
    except ValidationError as e:
        logger.error(f"Failed to parse article data: {e}")
        return "Failed: Invalid data schema"

    url = str(article_data.url)

    if es_client.article_exists(url):
        logger.info(f"Skipping {url} - already exists in database.")
        return "Skipped: Already exists"

    logger.info(f"Processing article: {url}")
    text = scraper.scrape_article(url)

    if not text:
        logger.warning(f"Aborting processing for {url} - No text extracted.")
        return "Failed: No text"

    success = es_client.index_article(article_data, text)
    if not success:
        return "Failed: Elasticsearch indexing error"

    logger.info(f"Executing NLP sentiment and ABSA analysis for: {url}")
    try:
        nlp_payload = nlp_processor.process_article(text)
    except Exception as e:
        logger.error(f"Error inside NLP processor for {url}: {e}", exc_info=True)
        return "Partial Success: Base article saved, NLP evaluation failed"

    doc_id = es_client.get_doc_id(url)

    nlp_updated = es_client.update_article_nlp(doc_id, nlp_payload)
    if not nlp_updated:
        logger.warning(
            f"Task completing with Partial Success. NLP update failed for {url}"
        )
        return "Partial Success: Base article saved, Elasticsearch update failed"

    return "Success"
