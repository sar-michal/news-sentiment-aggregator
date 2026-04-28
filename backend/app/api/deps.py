from fastapi import Request

from app.services.es_search import AsyncSearchClient


def get_search_client(request: Request) -> AsyncSearchClient:
    """Dependency to retrieve the global async search client from app state."""
    return request.app.state.search_client
