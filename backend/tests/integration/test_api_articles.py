from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.deps import get_search_client
from app.main import app
from app.schemas.api import ArticleListResponse, ArticleResponse
from fastapi.testclient import TestClient


@pytest.fixture
def mock_article_response():
    return ArticleListResponse(
        total_results=1,
        page=1,
        size=20,
        total_pages=1,
        articles=[
            ArticleResponse(
                id="fake-hash",
                url="https://example.com/news",
                title="Economy Crashes",
                seendate=datetime(2023, 10, 24, 15, 30, tzinfo=timezone.utc),
                domain="example.com",
                sourcecountry="US",
                sentiment_score=0.7,
                entities=[],
                timeline=[],
                snippets=None,
            )
        ],
    )


@pytest.fixture
def mock_search_client():
    mock_client = MagicMock()
    app.dependency_overrides[get_search_client] = lambda: mock_client
    try:
        yield mock_client
    finally:
        app.dependency_overrides.clear()


def test_search_articles_success(mock_article_response, mock_search_client):
    mock_search_client.search_articles = AsyncMock(return_value=mock_article_response)

    with TestClient(app) as client:
        response = client.get("/api/v1/articles/", params={"query_str": "economy"})

    mock_search_client.search_articles.assert_awaited_once_with(
        query_str="economy",
        domain=None,
        page=1,
        size=20,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_results"] == 1
    assert data["articles"][0]["title"] == "Economy Crashes"


def test_search_articles_503_connection_error(mock_search_client):
    mock_search_client.search_articles = AsyncMock(
        side_effect=ConnectionError("DB down")
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/articles/", params={"query_str": "economy"})

    mock_search_client.search_articles.assert_awaited_once_with(
        query_str="economy",
        domain=None,
        page=1,
        size=20,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Search service is temporarily unavailable."


def test_search_articles_500_runtime_error(mock_search_client):
    mock_search_client.search_articles = AsyncMock(
        side_effect=RuntimeError("Unexpected error")
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/articles/", params={"query_str": "economy"})

    mock_search_client.search_articles.assert_awaited_once_with(
        query_str="economy",
        domain=None,
        page=1,
        size=20,
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "An internal search error occurred."


def test_search_articles_422_validation_error():
    with TestClient(app) as client:
        response = client.get("/api/v1/articles/", params={"page": 0})

    assert response.status_code == 422
    assert "page" in response.json()["detail"][0]["loc"]
