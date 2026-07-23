from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_search_client
from app.schemas.api import DomainListResponse
from app.services.es_search import AsyncSearchClient

router = APIRouter()


@router.get("/domains", response_model=DomainListResponse)
async def get_domains(
    client: AsyncSearchClient = Depends(get_search_client),
):
    """
    Retrieves a list of all article domains present in the index.
    """
    try:
        return await client.get_domains()
    except ConnectionError:
        raise HTTPException(
            status_code=503, detail="Search service is temporarily unavailable."
        )
    except Exception:
        raise HTTPException(
            status_code=500, detail="An internal search error occurred."
        )
