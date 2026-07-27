from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_search_client
from app.schemas.api import ArticleListResponse, ArticleResponse
from app.services.es_search import AsyncSearchClient

router = APIRouter()


@router.get("/", response_model=ArticleListResponse)
async def search_articles(
    query_str: str | None = Query(None, description="Search query string"),
    domain: str | None = Query(None, description="Filter by specific domain"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    client: AsyncSearchClient = Depends(get_search_client),
):
    try:
        return await client.search_articles(
            query_str=query_str, domain=domain, page=page, size=size
        )
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: str,
    client: AsyncSearchClient = Depends(get_search_client),
):
    try:
        article = await client.get_article(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        return article
    except HTTPException:
        raise
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )
