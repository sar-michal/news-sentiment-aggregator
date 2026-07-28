from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_search_client
from app.schemas.api import SentimentTrendResponse, TopEntitiesResponse
from app.services.es_search import AsyncSearchClient

router = APIRouter()


@router.get("/sentiment-trend", response_model=SentimentTrendResponse)
async def get_sentiment_trend(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("day", description="Aggregation interval (day, week, month)"),
    domain: str | None = Query(None, description="Filter by specific domain"),
    client: AsyncSearchClient = Depends(get_search_client),
):
    """
    Returns time-series data of average sentiment.
    """
    try:
        return await client.get_sentiment_trend(
            start_date=start_date, end_date=end_date, interval=interval, domain=domain
        )
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )


@router.get("/top-entities", response_model=TopEntitiesResponse)
async def get_top_entities(
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    domain: str | None = None,
    min_mentions: int = Query(5, description="Minimum occurrences to be included"),
    client: AsyncSearchClient = Depends(get_search_client),
):
    """
    Returns the most positively and negatively discussed entities.
    """
    try:
        return await client.get_top_entities(
            start_date=start_date,
            end_date=end_date,
            domain=domain,
            min_mentions=min_mentions,
        )
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )
