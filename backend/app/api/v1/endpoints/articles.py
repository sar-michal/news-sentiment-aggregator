from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_search_client
from app.schemas.api import ArticleListResponse
from app.services.es_search import AsyncSearchClient

router = APIRouter()


@router.get("/", response_model=ArticleListResponse)
async def search_articles(
    query_str: str | None = Query(None, description="Search query string"),
    domain: str | None = Query(None, description="Filter by specific domain"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    client: AsyncSearchClient = Depends(get_search_client),
):
    try:
        return await client.search_articles(
            query_str=query_str, domain=domain, page=page
        )
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )
