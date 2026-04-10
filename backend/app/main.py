import json

from fastapi import FastAPI

from app.core.config import Environment, settings
from app.core.logging_config import setup_logging
from app.services.es_search import AsyncSearchClient
from app.services.gdelt import GdeltFetcher
from app.services.scraper import NewsScraper
from app.workers.tasks import trigger_gdelt_fetch

setup_logging()

app = FastAPI(
    title="News Sentiment Aggregator API",
    version="0.1.0",
    docs_url="/docs" if settings.ENVIRONMENT != Environment.PRODUCTION else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != Environment.PRODUCTION else None,
    openapi_url="/openapi.json"
    if settings.ENVIRONMENT != Environment.PRODUCTION
    else None,
)


@app.get("/")
async def root():
    return {"status": "ok", "message": "ok"}


# --- TEST ROUTES ---
@app.get("/test-gdelt")
async def test_gdelt():
    fetcher = GdeltFetcher()
    articles = fetcher.fetch_latest_news(max_records=10)

    return {"count": len(articles), "data": articles}


@app.get("/test-scrape")
async def test_scrape():
    with open("/app/app/test_articles.json", "r") as file:
        test_articles = json.load(file)

    if not test_articles:
        return {"message": "No articles found"}

    scraper = NewsScraper()

    with open("test_scrape2.txt", "a", encoding="utf-8") as output_file:
        for item in test_articles["data"]:
            url = item.get("url")
            if url:
                print(scraper.scrape_article(url), file=output_file)
    return {"status": "ok"}


@app.get("/test-celery")
def test_celery_integration():
    task = trigger_gdelt_fetch.delay()

    return {"message": "Task sent to Celery successfully!", "task_id": task.id}


@app.get("/test-search")
async def test_search(q: str | None = None, domain: str | None = None, page: int = 1):
    client = AsyncSearchClient()
    try:
        results = await client.search_articles(
            query_str=q, domain=domain, page=page, size=3
        )
        if not results:
            return {"message": "No results or connection failed"}
        return results
    finally:
        await client.close()
