from unittest.mock import AsyncMock


def test_get_sentiment_trend_success(client, mock_search_client):
    mock_response = {
        "trends": [{"date": "2023-10-24", "avg_sentiment": 0.5, "doc_count": 10}]
    }
    mock_search_client.get_sentiment_trend = AsyncMock(return_value=mock_response)

    response = client.get(
        "/api/v1/analytics/sentiment-trend",
        params={"interval": "week", "domain": "cnn.com"},
    )

    mock_search_client.get_sentiment_trend.assert_awaited_once_with(
        start_date=None, end_date=None, interval="week", domain="cnn.com"
    )
    assert response.status_code == 200
    assert response.json()["trends"][0]["avg_sentiment"] == 0.5


def test_get_sentiment_trend_503(client, mock_search_client):
    mock_search_client.get_sentiment_trend = AsyncMock(side_effect=ConnectionError())
    response = client.get("/api/v1/analytics/sentiment-trend")
    assert response.status_code == 503


def test_get_top_entities_success(client, mock_search_client):
    mock_response = {
        "most_positive": [
            {
                "entity": "Apple",
                "type": "ORG",
                "avg_sentiment": 0.8,
                "sum_sentiment": 8.0,
                "mention_count": 10,
            }
        ],
        "most_negative": [],
    }
    mock_search_client.get_top_entities = AsyncMock(return_value=mock_response)

    response = client.get("/api/v1/analytics/top-entities", params={"min_mentions": 10})

    mock_search_client.get_top_entities.assert_awaited_once_with(
        start_date=None, end_date=None, min_mentions=10
    )
    assert response.status_code == 200
    assert response.json()["most_positive"][0]["entity"] == "Apple"


def test_get_top_entities_500(client, mock_search_client):
    mock_search_client.get_top_entities = AsyncMock(side_effect=Exception("Crash"))
    response = client.get("/api/v1/analytics/top-entities")
    assert response.status_code == 500
