from unittest.mock import MagicMock

import app.workers.tasks as tasks_module
import pytest
from app.workers.tasks import process_article, trigger_gdelt_fetch


@pytest.fixture(autouse=True)
def setup_task_globals(monkeypatch):
    """
    Because global worker services are initialized asynchronously via
    @worker_process_init in Celery, they are `None` during pytest runs.
    This fixture automatically initializes them as MagicMocks for every test.
    """
    monkeypatch.setattr(tasks_module, "gdelt_fetcher", MagicMock())
    monkeypatch.setattr(tasks_module, "scraper", MagicMock())
    monkeypatch.setattr(tasks_module, "es_client", MagicMock())
    monkeypatch.setattr(tasks_module, "nlp_processor", MagicMock())


def test_trigger_gdelt_fetch_returns_empty_message_when_no_articles(monkeypatch):
    tasks_module.gdelt_fetcher.fetch_latest_news.return_value = []

    mock_delay = MagicMock()
    monkeypatch.setattr(process_article, "delay", mock_delay)

    actual = trigger_gdelt_fetch()

    assert actual == "No articles queued."
    mock_delay.assert_not_called()


def test_trigger_gdelt_fetch_queues_articles_and_returns_summary(monkeypatch):
    mock_article_1 = MagicMock()
    mock_article_1.model_dump.return_value = {
        "url": "https://example.com/1",
        "title": "A",
    }
    mock_article_2 = MagicMock()
    mock_article_2.model_dump.return_value = {
        "url": "https://example.com/2",
        "title": "B",
    }

    tasks_module.gdelt_fetcher.fetch_latest_news.return_value = [
        mock_article_1,
        mock_article_2,
    ]

    mock_delay = MagicMock()
    monkeypatch.setattr(process_article, "delay", mock_delay)

    actual = trigger_gdelt_fetch()

    assert actual == "Queued 2 articles for processing."
    assert mock_delay.call_count == 2
    mock_delay.assert_any_call({"url": "https://example.com/1", "title": "A"})
    mock_delay.assert_any_call({"url": "https://example.com/2", "title": "B"})


def test_trigger_gdelt_fetch_propagates_exceptions_for_celery_retry():
    tasks_module.gdelt_fetcher.fetch_latest_news.side_effect = ConnectionError(
        "Simulated GDELT failure"
    )

    with pytest.raises(ConnectionError, match="Simulated GDELT failure"):
        trigger_gdelt_fetch()


def test_process_article_handles_malformed_dictionary_gracefully():
    actual = process_article({})

    assert actual == "Failed: Invalid data schema"


def test_process_article_skips_existing_articles():
    tasks_module.es_client.article_exists.return_value = True

    article_data = {
        "url": "https://example.com/existing-article",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Skipped: Already exists"
    tasks_module.scraper.scrape_article.assert_not_called()


def test_process_article_returns_failed_when_no_text_extracted():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.return_value = None

    article_data = {
        "url": "https://example.com/bad-article",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Failed: No text"


def test_process_article_returns_failed_es_error_on_indexing_failure():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.return_value = "Extracted article text"
    tasks_module.es_client.index_article.return_value = False

    article_data = {
        "url": "https://example.com/es-fail",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Failed: Elasticsearch indexing error"


def test_process_article_propagates_exceptions_for_celery_retry():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.side_effect = ConnectionError(
        "Trafilatura failed"
    )

    article_data = {
        "url": "https://example.com/timeout",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    with pytest.raises(ConnectionError, match="Trafilatura failed"):
        process_article(article_data)


def test_process_article_returns_partial_success_on_nlp_failure():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.return_value = "Extracted article text"
    tasks_module.es_client.index_article.return_value = True

    tasks_module.nlp_processor.process_article.side_effect = Exception("Model crashed")

    article_data = {
        "url": "https://example.com/nlp-fail",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Partial Success: Base article saved, NLP evaluation failed"
    tasks_module.nlp_processor.process_article.assert_called_once_with(
        "Extracted article text"
    )
    tasks_module.es_client.update_article_nlp.assert_not_called()


def test_process_article_returns_partial_success_on_es_update_failure():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.return_value = "Extracted article text"
    tasks_module.es_client.index_article.return_value = True

    fake_nlp_payload = {"sentences": [], "entities": [], "sentiment_score": 0.5}
    tasks_module.nlp_processor.process_article.return_value = fake_nlp_payload
    tasks_module.es_client.get_doc_id.return_value = "fake_doc_id"
    tasks_module.es_client.update_article_nlp.return_value = False

    article_data = {
        "url": "https://example.com/es-update-fail",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Partial Success: Base article saved, Elasticsearch update failed"
    tasks_module.nlp_processor.process_article.assert_called_once_with(
        "Extracted article text"
    )
    tasks_module.es_client.get_doc_id.assert_called_once_with(
        "https://example.com/es-update-fail"
    )
    tasks_module.es_client.update_article_nlp.assert_called_once_with(
        "fake_doc_id", fake_nlp_payload
    )


def test_process_article_returns_success_when_extracted_indexed_and_nlp_updated():
    tasks_module.es_client.article_exists.return_value = False
    tasks_module.scraper.scrape_article.return_value = "Extracted article text"
    tasks_module.es_client.index_article.return_value = True

    fake_nlp_payload = {"sentences": [], "entities": [], "sentiment_score": 0.5}
    tasks_module.nlp_processor.process_article.return_value = fake_nlp_payload
    tasks_module.es_client.get_doc_id.return_value = "fake_doc_id"
    tasks_module.es_client.update_article_nlp.return_value = True

    article_data = {
        "url": "https://example.com/good-article",
        "title": "Title",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "United States",
    }

    actual = process_article(article_data)

    assert actual == "Success"
    tasks_module.nlp_processor.process_article.assert_called_once_with(
        "Extracted article text"
    )
    tasks_module.es_client.get_doc_id.assert_called_once_with(
        "https://example.com/good-article"
    )
    tasks_module.es_client.update_article_nlp.assert_called_once_with(
        "fake_doc_id", fake_nlp_payload
    )
