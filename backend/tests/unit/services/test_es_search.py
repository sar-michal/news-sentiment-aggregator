from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.es_search import AsyncSearchClient
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import NotFoundError


@pytest.fixture
def mock_es(monkeypatch):
    """Mock the AsyncElasticsearch client with pytest."""
    mock_instance = MagicMock()

    # Default successful response shape to prevent formatting crashes
    mock_instance.search = AsyncMock(
        return_value={"hits": {"total": {"value": 0}, "hits": []}}
    )
    mock_instance.get = AsyncMock()

    monkeypatch.setattr(
        "app.services.es_search.AsyncElasticsearch",
        lambda *args, **kwargs: mock_instance,
    )
    return mock_instance


@pytest.fixture
def search_client(mock_es):
    """Returns an AsyncSearchClient instance that uses the mocked ES underneath."""
    return AsyncSearchClient()


# --- SEARCH ARTICLES TESTS ---


@pytest.mark.asyncio
async def test_search_articles_raises_connection_error_on_es_failure(
    search_client, mock_es
):
    mock_es.search.side_effect = ESConnectionError("DB down")

    with pytest.raises(ConnectionError, match="Database connection failed"):
        await search_client.search_articles()


@pytest.mark.asyncio
async def test_search_articles_raises_runtime_error_on_unexpected_exception(
    search_client, mock_es
):
    mock_es.search.side_effect = Exception("Unexpected exception")

    with pytest.raises(RuntimeError, match="Internal search execution failed"):
        await search_client.search_articles()


@pytest.mark.asyncio
async def test_search_articles_builds_match_all_when_query_empty(
    search_client, mock_es
):
    await search_client.search_articles()

    call_args = mock_es.search.call_args[1]
    assert call_args["query"]["bool"]["must"][0] == {"match_all": {}}
    assert call_args["query"]["bool"]["filter"] == []
    assert call_args["from_"] == 0
    assert call_args["size"] == 20
    assert call_args["sort"] == [{"seendate": {"order": "desc"}}]


@pytest.mark.asyncio
async def test_search_articles_builds_filtered_query_with_params(
    search_client, mock_es
):
    await search_client.search_articles(
        query_str="economy", domain="cnn.com", page=2, size=50
    )

    call_args = mock_es.search.call_args[1]
    assert "multi_match" in call_args["query"]["bool"]["must"][0]
    assert call_args["query"]["bool"]["filter"][0] == {"term": {"domain": "cnn.com"}}
    assert call_args["from_"] == 50
    assert call_args["size"] == 50
    assert call_args["sort"] == [{"seendate": {"order": "desc"}}]


def test_format_response_handles_empty_hits(search_client):
    es_response = {"hits": {"total": {"value": 0, "relation": "eq"}, "hits": []}}

    response = search_client._format_response(es_response, page=1, size=20)

    assert response.total_results == 0
    assert response.total_pages == 0
    assert response.articles == []


def test_format_response_maps_sentences_and_entities_correctly(search_client):
    es_response = {
        "hits": {
            "total": {"value": 1, "relation": "eq"},
            "hits": [
                {
                    "_id": "hash123",
                    "_source": {
                        "url": "https://example.com/1",
                        "title": "Data Test",
                        "domain": "example.com",
                        "sourcecountry": "US",
                        "seendate": "2023-10-24T15:30:00Z",
                        "entities": [
                            {"entity": "Apple", "type": "ORG", "sentiment": 0.5}
                        ],
                        "sentences": [
                            {
                                "sequence_index": 0,
                                "text": "Neutral.",
                                "sentiment_score": 0.1,
                            },
                            {
                                "sequence_index": 1,
                                "text": "Terrible!",
                                "sentiment_score": -0.9,
                            },
                            {
                                "sequence_index": 2,
                                "text": "Unscored.",
                                "sentiment_score": None,
                            },
                            {
                                "sequence_index": 3,
                                "text": "Amazing!",
                                "sentiment_score": 0.8,
                            },
                        ],
                    },
                }
            ],
        }
    }

    response = search_client._format_response(es_response, page=1, size=20)

    article = response.articles[0]
    assert len(article.entities) == 1
    assert article.entities[0].entity == "Apple"
    assert len(article.timeline) == 3
    assert article.timeline[1].sentiment_score == -0.9
    assert article.snippets.most_negative == "Terrible!"
    assert article.snippets.most_positive == "Amazing!"


# --- GET ARTICLE TESTS ---


@pytest.mark.asyncio
async def test_get_article_returns_mapped_schema(search_client, mock_es):
    mock_es.get.return_value = {
        "_id": "id123",
        "_source": {
            "url": "https://bbc.co.uk",
            "title": "Breaking News",
            "domain": "bbc.co.uk",
            "sourcecountry": "UK",
            "seendate": "2023-10-25T10:00:00Z",
            "sentences": [
                {"sequence_index": 0, "text": "Test.", "sentiment_score": 0.5}
            ],
        },
    }
    res = await search_client.get_article("id123")
    assert res is not None
    assert res.id == "id123"
    assert res.title == "Breaking News"
    assert res.snippets.most_positive == "Test."


@pytest.mark.asyncio
async def test_get_article_returns_none_on_404(search_client, mock_es):
    mock_es.get.side_effect = NotFoundError(404, "Not Found", {})
    res = await search_client.get_article("fake_id")
    assert res is None


@pytest.mark.asyncio
async def test_get_article_raises_connection_error_on_failure(search_client, mock_es):
    mock_es.get.side_effect = ESConnectionError("Offline")
    with pytest.raises(ConnectionError, match="Database connection failed"):
        await search_client.get_article("id123")


# --- SENTIMEMT TREND TESTS ---


@pytest.mark.asyncio
async def test_get_sentiment_trend_builds_aggregations(search_client, mock_es):
    mock_es.search.return_value = {
        "aggregations": {
            "trend": {
                "buckets": [
                    {
                        "key_as_string": "2023-10-24",
                        "key": 1698105600000,
                        "doc_count": 10,
                        "avg_sentiment": {"value": 0.25},
                    }
                ]
            }
        }
    }

    res = await search_client.get_sentiment_trend(
        start_date="2023-10-01", domain="reuters.com"
    )

    call_args = mock_es.search.call_args[1]
    assert call_args["size"] == 0
    assert call_args["query"]["bool"]["filter"][0] == {
        "term": {"domain": "reuters.com"}
    }
    assert res["trends"][0]["avg_sentiment"] == 0.25
    assert res["trends"][0]["date"] == "2023-10-24"


# --- TOP ENTITIES TESTS ---


@pytest.mark.asyncio
async def test_get_top_entities_builds_nested_aggregation_and_formats_results(
    search_client, mock_es
):
    mock_es.search.return_value = {
        "aggregations": {
            "nested_entities": {
                "most_positive": {
                    "buckets": [
                        {
                            "key": "Apple",
                            "doc_count": 8,
                            "sum_sentiment": {"value": 5.6},
                            "avg_sentiment": {"value": 0.7},
                            "entity_type": {"buckets": [{"key": "ORG"}]},
                        }
                    ]
                },
                "most_negative": {
                    "buckets": [
                        {
                            "key": "Tesla",
                            "doc_count": 6,
                            "sum_sentiment": {"value": -4.8},
                            "avg_sentiment": {"value": -0.8},
                            "entity_type": {"buckets": [{"key": "ORG"}]},
                        }
                    ]
                },
            }
        }
    }

    result = await search_client.get_top_entities(
        start_date="2024-01-01", end_date="2024-01-31", min_mentions=5
    )

    call_args = mock_es.search.call_args[1]
    assert call_args["index"] == search_client.index_name
    assert call_args["size"] == 0
    assert "nested_entities" in call_args["aggs"]

    assert result["most_positive"][0]["entity"] == "Apple"
    assert result["most_negative"][0]["sum_sentiment"] == -4.8


@pytest.mark.asyncio
async def test_get_top_entities_raises_connection_error_on_es_failure(
    search_client, mock_es
):
    mock_es.search.side_effect = ESConnectionError("cluster offline")

    with pytest.raises(ConnectionError, match="Database connection failed"):
        await search_client.get_top_entities()


# --- GET DOMAINS TESTS ---


@pytest.mark.asyncio
async def test_get_domains_extracts_keys(search_client, mock_es):
    mock_es.search.return_value = {
        "aggregations": {
            "unique_domains": {
                "buckets": [
                    {"key": "cnn.com", "doc_count": 50},
                    {"key": "bbc.com", "doc_count": 40},
                ]
            }
        }
    }

    res = await search_client.get_domains()
    assert res["domains"] == ["cnn.com", "bbc.com"]


@pytest.mark.asyncio
async def test_get_domains_raises_runtime_error_on_generic_exception(
    search_client, mock_es
):
    mock_es.search.side_effect = Exception("Crash")
    with pytest.raises(RuntimeError, match="Failed to fetch domains"):
        await search_client.get_domains()


# --- ERROR HANDLING TESTS ---


@pytest.mark.asyncio
async def test_get_sentiment_trend_raises_runtime_error_on_generic_exception(
    search_client, mock_es
):
    mock_es.search.side_effect = Exception("Crash")
    with pytest.raises(RuntimeError, match="Failed to fetch sentiment trend"):
        await search_client.get_sentiment_trend()


@pytest.mark.asyncio
async def test_get_top_entities_raises_runtime_error_on_generic_exception(
    search_client, mock_es
):
    mock_es.search.side_effect = Exception("Crash")
    with pytest.raises(RuntimeError, match="Failed to fetch top entities"):
        await search_client.get_top_entities()


# --- GET ENTITY ANALYSIS TESTS ---


@pytest.mark.asyncio
async def test_get_entity_analysis_builds_query_and_formats_results(
    search_client, mock_es
):
    mock_es.search.return_value = {
        "aggregations": {
            "overall_nested": {
                "match_entity": {
                    "doc_count": 100,
                    "avg_sentiment": {"value": 0.5},
                    "sum_sentiment": {"value": 50.0},
                }
            },
            "domains": {
                "buckets": [
                    {
                        "key": "cnn.com",
                        "entity_nested": {
                            "match_entity": {
                                "doc_count": 60,
                                "avg_sentiment": {"value": 0.6},
                                "sum_sentiment": {"value": 36.0},
                            }
                        },
                    }
                ]
            },
        }
    }

    res = await search_client.get_entity_analysis(
        entity_name="Apple", start_date="2026-01-01"
    )

    call_args = mock_es.search.call_args[1]
    assert call_args["size"] == 0
    assert (
        call_args["query"]["bool"]["must"][0]["nested"]["query"]["term"][
            "entities.entity"
        ]
        == "Apple"
    )

    assert res["entity"] == "Apple"
    assert res["total_mentions"] == 100
    assert res["overall_avg_sentiment"] == 0.5
    assert len(res["domains"]) == 1
    assert res["domains"][0]["domain"] == "cnn.com"
    assert res["domains"][0]["mention_count"] == 60


@pytest.mark.asyncio
async def test_get_entity_analysis_raises_connection_error_on_failure(
    search_client, mock_es
):
    mock_es.search.side_effect = ESConnectionError("Offline")
    with pytest.raises(ConnectionError, match="Database connection failed"):
        await search_client.get_entity_analysis("Apple")


@pytest.mark.asyncio
async def test_get_entity_analysis_raises_runtime_error_on_failure(
    search_client, mock_es
):
    mock_es.search.side_effect = Exception("Crash")
    with pytest.raises(RuntimeError, match="Failed to fetch entity analysis"):
        await search_client.get_entity_analysis("Apple")


# --- SUGGEST ENTITIES TESTS ---


@pytest.mark.asyncio
async def test_suggest_entities_returns_early_on_short_prefix(search_client, mock_es):
    res = await search_client.suggest_entities("A")
    assert res == []
    mock_es.search.assert_not_called()


@pytest.mark.asyncio
async def test_suggest_entities_builds_prefix_query_and_extracts_keys(
    search_client, mock_es
):
    mock_es.search.return_value = {
        "aggregations": {
            "entity_nested": {
                "filtered_entities": {
                    "entity_names": {
                        "buckets": [
                            {"key": "Apple", "doc_count": 50},
                            {"key": "Apple Inc", "doc_count": 20},
                        ]
                    }
                }
            }
        }
    }

    res = await search_client.suggest_entities("App")

    call_args = mock_es.search.call_args[1]
    filter_val = call_args["aggs"]["entity_nested"]["aggs"]["filtered_entities"][
        "filter"
    ]
    assert filter_val["prefix"]["entities.entity"]["value"] == "App"
    assert filter_val["prefix"]["entities.entity"]["case_insensitive"] is True

    assert res == ["Apple", "Apple Inc"]


@pytest.mark.asyncio
async def test_suggest_entities_returns_empty_list_on_exception(search_client, mock_es):
    mock_es.search.side_effect = Exception("Crash")
    res = await search_client.suggest_entities("App")
    assert res == []
