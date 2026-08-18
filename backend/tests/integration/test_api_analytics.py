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


def test_get_sentiment_trend_500(client, mock_search_client):
    mock_search_client.get_sentiment_trend = AsyncMock(
        side_effect=RuntimeError("Crash")
    )
    response = client.get("/api/v1/analytics/sentiment-trend")
    assert response.status_code == 500


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
        start_date=None, end_date=None, domain=None, min_mentions=10
    )
    assert response.status_code == 200
    assert response.json()["most_positive"][0]["entity"] == "Apple"


def test_get_top_entities_with_filters(client, mock_search_client):
    mock_search_client.get_top_entities = AsyncMock(
        return_value={"most_positive": [], "most_negative": []}
    )

    response = client.get(
        "/api/v1/analytics/top-entities",
        params={
            "domain": "bbc.co.uk",
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "min_mentions": 5,
        },
    )

    mock_search_client.get_top_entities.assert_awaited_once_with(
        start_date="2026-01-01",
        end_date="2026-12-31",
        domain="bbc.co.uk",
        min_mentions=5,
    )
    assert response.status_code == 200


def test_get_top_entities_503(client, mock_search_client):
    mock_search_client.get_top_entities = AsyncMock(
        side_effect=ConnectionError("DB offline")
    )
    response = client.get("/api/v1/analytics/top-entities")
    assert response.status_code == 503


def test_get_top_entities_500(client, mock_search_client):
    mock_search_client.get_top_entities = AsyncMock(side_effect=Exception("Crash"))
    response = client.get("/api/v1/analytics/top-entities")
    assert response.status_code == 500


def test_get_entity_analysis_success(client, mock_search_client):
    mock_response = {
        "entity": "Apple",
        "total_mentions": 100,
        "overall_avg_sentiment": 0.5,
        "overall_sum_sentiment": 50.0,
        "domains": [
            {
                "domain": "cnn.com",
                "mention_count": 50,
                "avg_sentiment": 0.6,
                "sum_sentiment": 30.0,
            }
        ],
    }
    mock_search_client.get_entity_analysis = AsyncMock(return_value=mock_response)

    response = client.get(
        "/api/v1/analytics/entity-analysis",
        params={"entity": "Apple", "start_date": "2026-01-01"},
    )

    mock_search_client.get_entity_analysis.assert_awaited_once_with(
        entity_name="Apple", start_date="2026-01-01", end_date=None
    )
    assert response.status_code == 200
    assert response.json()["entity"] == "Apple"
    assert len(response.json()["domains"]) == 1


def test_get_entity_analysis_503(client, mock_search_client):
    mock_search_client.get_entity_analysis = AsyncMock(
        side_effect=ConnectionError("DB offline")
    )
    response = client.get(
        "/api/v1/analytics/entity-analysis", params={"entity": "Apple"}
    )
    assert response.status_code == 503


def test_get_entity_analysis_500(client, mock_search_client):
    mock_search_client.get_entity_analysis = AsyncMock(side_effect=Exception("Crash"))
    response = client.get(
        "/api/v1/analytics/entity-analysis", params={"entity": "Apple"}
    )
    assert response.status_code == 500


def test_entity_suggest_success(client, mock_search_client):
    mock_search_client.suggest_entities = AsyncMock(return_value=["Apple", "Apple Inc"])

    response = client.get("/api/v1/analytics/entity-suggest", params={"prefix": "App"})

    mock_search_client.suggest_entities.assert_awaited_once_with(prefix="App")
    assert response.status_code == 200
    assert response.json()["suggestions"] == [{"name": "Apple"}, {"name": "Apple Inc"}]


def test_entity_suggest_500(client, mock_search_client):
    mock_search_client.suggest_entities = AsyncMock(side_effect=Exception("Crash"))
    response = client.get("/api/v1/analytics/entity-suggest", params={"prefix": "App"})
    assert response.status_code == 500
