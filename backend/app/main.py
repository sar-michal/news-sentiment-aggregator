from fastapi import FastAPI
from app.core.logging_config import setup_logging
import json
from app.services.gdelt import GdeltFetcher
from app.services.scraper import NewsScraper

setup_logging()

app = FastAPI(
    title="News Sentiment Aggregator API",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "ok"}

# --- TEST ROUTES ---
@app.get("/test-gdelt")
async def test_gdelt():
    fetcher = GdeltFetcher()
    articles = fetcher.fetch_latest_news(max_records=10)
    
    return {
        "count": len(articles),
        "data": articles
    }

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