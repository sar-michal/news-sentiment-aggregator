import logging

from app.services.gdelt import GdeltFetcher
from app.services.scraper import NewsScraper
from app.workers.celery_app import celery

logger = logging.getLogger(__name__)


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

    gdelt_fetcher = GdeltFetcher()
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
def process_article(self, article_data: dict):
    """Consumer: Downloads HTML and extracts article text."""
    url = article_data.get("url")
    logger.info(f"Processing article: {url}")

    scraper = NewsScraper()
    text = scraper.scrape_article(url)

    if not text:
        logger.warning(f"Aborting processing for {url} - No text extracted.")
        return "Failed: No text"

    # TODO: Add sentiment analysis

    # TODO: Add storing to Elasticsearch

    return "Success"
