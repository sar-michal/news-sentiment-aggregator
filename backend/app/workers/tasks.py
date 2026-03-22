import logging

from celery.signals import worker_process_init
from pydantic import ValidationError

from app.schemas.article import ArticleData
from app.services.es_client import ElasticClient
from app.services.gdelt import GdeltFetcher
from app.services.scraper import NewsScraper
from app.workers.celery_app import celery

logger = logging.getLogger(__name__)

gdelt_fetcher = None
scraper = None
es_client = None


@worker_process_init.connect
def init_worker_services(**kwargs):
    """
    Celery Signal: Runs strictly once when the worker process boots up.
    """
    global gdelt_fetcher, scraper, es_client
    logger.info("Initializing global worker services and connection pools...")
    gdelt_fetcher = GdeltFetcher()
    scraper = NewsScraper()
    es_client = ElasticClient()

    es_client.create_index()


@celery.task(
    bind=True,
    max_retries=3,
    autoretry_for=(ConnectionError,),
    retry_backoff=60,
    retry_jitter=True,
)
def trigger_gdelt_fetch(self):
    """Producer: Fetches the latest GDELT articles and queues respective scraping tasks."""
    logger.info("Starting GDELT fetch...")
    articles = gdelt_fetcher.fetch_latest_news(max_records=50)

    if not articles:
        logger.info("No articles fetched this cycle.")
        return "No articles queued."

    for article in articles:
        article_dict = article.model_dump(mode="json")
        process_article.delay(article_dict)

    return f"Queued {len(articles)} articles for processing."


@celery.task(
    bind=True, max_retries=2, autoretry_for=(ConnectionError,), retry_backoff=30
)
def process_article(self, article_dict: dict):
    """Consumer: Downloads HTML and extracts article text."""
    try:
        article_data = ArticleData(**article_dict)
    except ValidationError as e:
        logger.error(f"Failed to parse article data: {e}")
        return "Failed: Invalid data schema"

    url = str(article_data.url)
    logger.info(f"Processing article: {url}")

    text = scraper.scrape_article(url)

    if not text:
        logger.warning(f"Aborting processing for {url} - No text extracted.")
        return "Failed: No text"

    success = es_client.index_article(article_data, text)
    if not success:
        return "Failed: Elasticsearch indexing error"

    # TODO: Add sentiment analysis

    return "Success"
