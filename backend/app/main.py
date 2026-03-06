from fastapi import FastAPI
from app.services.gdelt import GdeltFetcher

app = FastAPI(
    title="News Sentiment Aggregator API",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "ok"}

# --- TEST ROUTE ---
@app.get("/test-gdelt")
async def test_gdelt():
    fetcher = GdeltFetcher()
    articles = fetcher.fetch_latest_news(max_records=10)
    
    return {
        "count": len(articles),
        "data": articles
    }