from unittest.mock import MagicMock

import pytest
from app.services.gdelt import GdeltFetcher
from app.services.scraper import NewsScraper
from app.workers.tasks import process_article, trigger_gdelt_fetch


def test_trigger_gdelt_fetch_returns_empty_message_when_no_articles(monkeypatch):
    monkeypatch.setattr(GdeltFetcher, "fetch_latest_news", lambda *args, **kwargs: [])

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

    monkeypatch.setattr(
        GdeltFetcher,
        "fetch_latest_news",
        lambda *args, **kwargs: [mock_article_1, mock_article_2],
    )

    mock_delay = MagicMock()
    monkeypatch.setattr(process_article, "delay", mock_delay)

    actual = trigger_gdelt_fetch()

    assert actual == "Queued 2 articles for processing."
    assert mock_delay.call_count == 2
    mock_delay.assert_any_call({"url": "https://example.com/1", "title": "A"})
    mock_delay.assert_any_call({"url": "https://example.com/2", "title": "B"})


def test_trigger_gdelt_fetch_propagates_exceptions_for_celery_retry(monkeypatch):
    def mock_fetch_latest_news(*args, **kwargs):
        raise ConnectionError("Simulated GDELT failure")

    monkeypatch.setattr(GdeltFetcher, "fetch_latest_news", mock_fetch_latest_news)

    with pytest.raises(ConnectionError, match="Simulated GDELT failure"):
        trigger_gdelt_fetch()


def test_process_article_handles_malformed_dictionary_gracefully(monkeypatch):
    monkeypatch.setattr(NewsScraper, "scrape_article", lambda *args, **kwargs: None)

    actual = process_article({})

    assert actual == "Failed: No text"


def test_process_article_returns_failed_when_no_text_extracted(monkeypatch):
    monkeypatch.setattr(NewsScraper, "scrape_article", lambda *args, **kwargs: None)
    article_data = {"url": "https://example.com/bad-article"}

    actual = process_article(article_data)

    assert actual == "Failed: No text"


def test_process_article_returns_success_when_text_extracted(monkeypatch):
    monkeypatch.setattr(
        NewsScraper, "scrape_article", lambda *args, **kwargs: "Extracted article text"
    )
    article_data = {"url": "https://example.com/good-article"}

    actual = process_article(article_data)

    assert actual == "Success"


def test_process_article_propagates_exceptions_for_celery_retry(monkeypatch):
    def mock_scrape_article(*args, **kwargs):
        raise ConnectionError("Trafilatura failed")

    monkeypatch.setattr(NewsScraper, "scrape_article", mock_scrape_article)
    article_data = {"url": "https://example.com/timeout"}

    with pytest.raises(ConnectionError, match="Trafilatura failed"):
        process_article(article_data)
