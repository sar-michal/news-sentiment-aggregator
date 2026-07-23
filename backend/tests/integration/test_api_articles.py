from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from app.schemas.api import ArticleListResponse, ArticleResponse


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
def mock_single_article():
    return {
        "id": "doc123",
        "url": "https://example.com/1",
        "title": "Single Article",
        "seendate": "2023-10-24T15:30:00Z",
        "domain": "example.com",
        "sourcecountry": "US",
        "sentiment_score": 0.5,
        "entities": [],
        "timeline": [],
        "snippets": {"most_positive": "Good.", "most_negative": "Bad."},
    }


def test_search_articles_success(client, mock_article_response, mock_search_client):
    mock_search_client.search_articles = AsyncMock(return_value=mock_article_response)

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


def test_search_articles_503_connection_error(client, mock_search_client):
    mock_search_client.search_articles = AsyncMock(
        side_effect=ConnectionError("DB down")
    )

    response = client.get("/api/v1/articles/", params={"query_str": "economy"})

    mock_search_client.search_articles.assert_awaited_once_with(
        query_str="economy",
        domain=None,
        page=1,
        size=20,
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "Search service is temporarily unavailable."


def test_search_articles_500_runtime_error(client, mock_search_client):
    mock_search_client.search_articles = AsyncMock(
        side_effect=RuntimeError("Unexpected error")
    )

    response = client.get("/api/v1/articles/", params={"query_str": "economy"})

    mock_search_client.search_articles.assert_awaited_once_with(
        query_str="economy",
        domain=None,
        page=1,
        size=20,
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "An internal search error occurred."


def test_search_articles_422_validation_error(client):
    response = client.get("/api/v1/articles/", params={"page": 0})

    assert response.status_code == 422
    assert "page" in response.json()["detail"][0]["loc"]


def test_get_article_success(client, mock_single_article, mock_search_client):
    mock_search_client.get_article = AsyncMock(return_value=mock_single_article)

    response = client.get("/api/v1/articles/doc123")

    mock_search_client.get_article.assert_awaited_once_with("doc123")
    assert response.status_code == 200
    assert response.json()["id"] == "doc123"


def test_get_article_404_not_found(client, mock_search_client):
    mock_search_client.get_article = AsyncMock(return_value=None)

    response = client.get("/api/v1/articles/missing_doc")

    assert response.status_code == 404
    assert response.json()["detail"] == "Article not found"


def test_get_article_503_connection_error(client, mock_search_client):
    mock_search_client.get_article = AsyncMock(side_effect=ConnectionError("DB down"))

    response = client.get("/api/v1/articles/doc123")

    assert response.status_code == 503


def test_get_article_500_runtime_error(client, mock_search_client):
    mock_search_client.get_article = AsyncMock(side_effect=RuntimeError("Crash"))

    response = client.get("/api/v1/articles/doc123")

    assert response.status_code == 500
