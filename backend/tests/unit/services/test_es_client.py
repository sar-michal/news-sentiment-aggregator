import hashlib
import logging
from unittest.mock import MagicMock

import pytest
from app.schemas.article import ArticleData
from app.services.es_client import ElasticClient
from elasticsearch.exceptions import ConnectionError as ESConnectionError


@pytest.fixture
def mock_es(monkeypatch):
    """Mock the Elasticsearch client with pytest."""
    mock_instance = MagicMock()
    monkeypatch.setattr(
        "app.services.es_client.Elasticsearch", lambda *args, **kwargs: mock_instance
    )
    return mock_instance


@pytest.fixture
def es_client(mock_es):
    """Returns an ElasticClient instance that uses the mocked ES underneath."""
    # mock_es has already patched it.
    return ElasticClient()


@pytest.fixture
def sample_article():
    return ArticleData(
        url="https://example.com/es-test",
        title="Valid Test Article",
        seendate="20231024T153000Z",
        domain="example.com",
        sourcecountry="United States",
    )


def test_create_index_skips_if_already_exists(es_client, mock_es):
    mock_es.indices.exists.return_value = True

    es_client.create_index()

    mock_es.indices.exists.assert_called_once_with(index=es_client.index_name)
    mock_es.indices.create.assert_not_called()


def test_create_index_creates_new_if_missing(es_client, mock_es):
    mock_es.indices.exists.return_value = False

    es_client.create_index()

    mock_es.indices.exists.assert_called_once_with(index=es_client.index_name)
    mock_es.indices.create.assert_called_once()

    call_kwargs = mock_es.indices.create.call_args[1]
    assert call_kwargs["index"] == es_client.index_name
    assert "mappings" in call_kwargs
    assert "url" in call_kwargs["mappings"]["properties"]
    assert call_kwargs["mappings"]["properties"]["title"]["analyzer"] == "english"


def test_create_index_exception_is_logged_and_suppressed(es_client, mock_es, caplog):
    mock_es.indices.exists.return_value = False
    mock_es.indices.create.side_effect = Exception("Index creation completely failed")

    with caplog.at_level(logging.ERROR):
        es_client.create_index()

    assert f"Failed to create index {es_client.index_name}" in caplog.text
    assert "Index creation completely failed" in caplog.text


def test_index_article_success(es_client, mock_es, sample_article):
    mock_es.index.return_value = {"result": "created"}
    text_content = "Extracted article body content full of text."

    result = es_client.index_article(sample_article, text_content)

    assert result is True
    mock_es.index.assert_called_once()

    call_kwargs = mock_es.index.call_args[1]
    assert call_kwargs["index"] == es_client.index_name

    expected_hash = hashlib.sha256(str(sample_article.url).encode("utf-8")).hexdigest()
    assert call_kwargs["id"] == expected_hash

    doc = call_kwargs["document"]
    assert doc["url"] == str(sample_article.url)
    assert doc["title"] == sample_article.title
    assert doc["content"] == text_content
    assert doc["sentiment_score"] is None
    assert doc["entities"] == []
    assert doc["sentences"] == []


def test_index_article_raises_builtin_connection_error_on_es_failure(
    es_client, mock_es, sample_article
):
    mock_es.index.side_effect = ESConnectionError("Node unreachable")

    with pytest.raises(ConnectionError, match="Elasticsearch connection failed:"):
        es_client.index_article(sample_article, "Some text")


def test_index_article_suppresses_generic_exception(
    es_client, mock_es, sample_article, caplog
):
    mock_es.index.side_effect = Exception("Unknown Elasticsearch cluster error")

    with caplog.at_level(logging.ERROR):
        result = es_client.index_article(sample_article, "Some text")

    assert result is False
    assert f"Unexpected error indexing {sample_article.url}" in caplog.text
    assert "Unknown Elasticsearch cluster error" in caplog.text


def test_article_exists_returns_true_when_found(es_client, mock_es):
    mock_es.exists.return_value = True
    url = "https://example.com/check-me"
    expected_doc_id = hashlib.sha256(url.encode("utf-8")).hexdigest()

    result = es_client.article_exists(url)

    assert result is True
    mock_es.exists.assert_called_once_with(
        index=es_client.index_name, id=expected_doc_id
    )


def test_article_exists_returns_false_when_not_found(es_client, mock_es):
    mock_es.exists.return_value = False
    url = "https://example.com/check-me-not"
    expected_doc_id = hashlib.sha256(url.encode("utf-8")).hexdigest()

    result = es_client.article_exists(url)

    assert result is False
    mock_es.exists.assert_called_once_with(
        index=es_client.index_name, id=expected_doc_id
    )


def test_article_exists_returns_false_and_handles_exceptions(
    es_client, mock_es, caplog
):
    mock_es.exists.side_effect = Exception("ES cluster offline")
    url = "https://example.com/error-test"

    with caplog.at_level(logging.WARNING):
        result = es_client.article_exists(url)

    assert result is False
    assert f"Failed to check existence for {url}: ES cluster offline" in caplog.text


def test_get_doc_id(es_client):
    url = "https://example.com/test-article"
    expected_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

    actual_hash = es_client.get_doc_id(url)
    assert actual_hash == expected_hash


def test_update_article_nlp_returns_true_on_successful_update(es_client, monkeypatch):
    mock_update = MagicMock(return_value={"result": "updated"})
    monkeypatch.setattr(es_client.client, "update", mock_update)

    payload = {
        "sentences": [{"text": "Hello", "sentiment_score": 0.5}],
        "entities": [{"entity": "UN", "type": "ORG", "sentiment": 0.5}],
        "sentiment_score": 0.5,
    }

    result = es_client.update_article_nlp("fake_id_123", payload)

    assert result is True
    mock_update.assert_called_once_with(
        index=es_client.index_name,
        id="fake_id_123",
        doc={
            "sentences": payload["sentences"],
            "entities": payload["entities"],
            "sentiment_score": 0.5,
        },
    )


def test_update_article_nlp_returns_false_on_unexpected_result_status(
    es_client, monkeypatch
):
    mock_update = MagicMock(return_value={"result": "created"})
    monkeypatch.setattr(es_client.client, "update", mock_update)

    result = es_client.update_article_nlp("fake_id_123", {})

    assert result is False


def test_update_article_nlp_catches_exceptions_and_returns_false(
    es_client, monkeypatch
):
    mock_update = MagicMock(side_effect=Exception("Simulated Elasticsearch crash"))
    monkeypatch.setattr(es_client.client, "update", mock_update)

    result = es_client.update_article_nlp("fake_id_123", {})

    assert result is False
