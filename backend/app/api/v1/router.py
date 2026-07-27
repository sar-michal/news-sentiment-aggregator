from fastapi import APIRouter

from app.api.v1.endpoints.analytics import router as analytics_router
from app.api.v1.endpoints.articles import router as articles_router
from app.api.v1.endpoints.metadata import router as metadata_router

api_router = APIRouter()
api_router.include_router(articles_router, prefix="/articles", tags=["Articles"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(metadata_router, prefix="/metadata", tags=["Metadata"])
