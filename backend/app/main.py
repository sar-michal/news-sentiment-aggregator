from fastapi import FastAPI

app = FastAPI(
    title="News Sentiment Aggregator API",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"status": "ok", "message": "ok"}