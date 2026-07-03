from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.es_search import AsyncSearchClient
from elasticsearch.exceptions import ConnectionError as ESConnectionError


@pytest.fixture
def mock_es(monkeypatch):
    """Mock the AsyncElasticsearch client with pytest."""
    mock_instance = MagicMock()

    # Default successful response shape to prevent formatting crashes
    mock_instance.search = AsyncMock(
        return_value={"hits": {"total": {"value": 0}, "hits": []}}
    )

    monkeypatch.setattr(
        "app.services.es_search.AsyncElasticsearch",
        lambda *args, **kwargs: mock_instance,
    )
    return mock_instance


@pytest.fixture
def search_client(mock_es):
    """Returns an AsyncSearchClient instance that uses the mocked ES underneath."""
    return AsyncSearchClient()


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


def test_format_response_handles_missing_sentences_with_default_snippets(
    search_client,
):
    es_response = {
        "hits": {
            "total": {"value": 1},
            "hits": [
                {
                    "_id": "hash123",
                    "_source": {
                        "url": "https://example.com",
                        "title": "No Text",
                        "seendate": "2023-10-24T15:30:00Z",
                        "domain": "example.com",
                        "sourcecountry": "US",
                        "sentences": [],
                    },
                }
            ],
        }
    }

    response = search_client._format_response(es_response, page=1, size=20)

    article = response.articles[0]
    assert article.timeline == []
    assert article.snippets is not None
    assert article.snippets.most_positive is None
    assert article.snippets.most_negative is None
