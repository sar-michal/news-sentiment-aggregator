from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.services.es_search import AsyncSearchClient

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.search_client = AsyncSearchClient()
    yield
    await app.state.search_client.close()


app = FastAPI(title="News Sentiment API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():  # pragma: no cover
    return {"status": "ok", "message": "ok"}
