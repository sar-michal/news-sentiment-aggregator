import pytest
import responses
from app.core.config import settings
from app.services.gdelt import GdeltFetcher


@pytest.mark.parametrize(
    "input_url, expected",
    [
        ("https://example.com/news/politics/123", True),
        ("https://example.com/world-news", True),
        ("https://example.com/video/report", False),
        ("https://example.com/sports/hockey", False),
    ],
)
def test_is_valid_url_matches_against_blacklist(input_url, expected):
    fetcher = GdeltFetcher()

    actual = fetcher._is_valid_url(input_url)

    assert actual is expected


def test_fetch_latest_news_filters_invalid_and_blacklisted_urls(
    block_requests_library,
):
    fetcher = GdeltFetcher()
    mock_payload = {
        "articles": [
            {
                "url": "https://example.com/news/1",
                "title": "Valid Article",
                "seendate": "20231024T153000Z",
                "domain": "example.com",
                "sourcecountry": "United States",
            },
            {
                "url": "https://test-domain.com/sports/1",
                "title": "Sports Match",
                "seendate": "20231024T154000Z",
                "domain": "test-domain.com",
                "sourcecountry": "United Kingdom",
            },
            {
                "url": "https://random-site.com/news",
                "title": "Not in Whitelist",
                "seendate": "20231024T155000Z",
                "domain": "random-site.com",
                "sourcecountry": "Poland",
            },
        ]
    }
    block_requests_library.add(
        responses.GET, fetcher.base_url, json=mock_payload, status=200
    )

    actual = fetcher.fetch_latest_news(max_records=10)

    assert len(actual) == 1
    assert actual[0].title == "Valid Article"
    assert str(actual[0].url) == "https://example.com/news/1"


def test_fetch_latest_news_gracefully_handles_rate_limits(
    block_requests_library,
):
    fetcher = GdeltFetcher()
    block_requests_library.add(responses.GET, fetcher.base_url, json={}, status=429)

    with pytest.raises(ConnectionError, match="HTTP 429: Too Many Requests"):
        fetcher.fetch_latest_news()


def test_fetch_latest_news_aborts_immediately_on_empty_whitelist(monkeypatch):
    monkeypatch.setattr(settings, "GDELT_WHITELIST", set())
    fetcher = GdeltFetcher()

    actual = fetcher.fetch_latest_news()

    assert actual == []


def test_fetch_latest_news_returns_empty_list_when_no_articles_key_present(
    block_requests_library,
):
    fetcher = GdeltFetcher()
    block_requests_library.add(
        responses.GET, fetcher.base_url, json={"some_other_key": "value"}, status=200
    )

    actual = fetcher.fetch_latest_news()

    assert actual == []


def test_fetch_latest_news_raises_connection_error_on_request_exception(
    block_requests_library,
):
    import requests

    fetcher = GdeltFetcher()
    block_requests_library.add(
        responses.GET,
        fetcher.base_url,
        body=requests.exceptions.RequestException("Simulated network dropping"),
    )

    with pytest.raises(ConnectionError, match="GDELT API connection failed"):
        fetcher.fetch_latest_news()


def test_fetch_latest_news_returns_empty_list_on_pydantic_validation_error(
    block_requests_library,
):
    fetcher = GdeltFetcher()
    malformed_payload = {
        "articles": [
            {
                "title": "Missing URL Article",
                "seendate": "20231024T153000Z",
                "domain": "example.com",
                "sourcecountry": "United States",
            }
        ]
    }
    block_requests_library.add(
        responses.GET, fetcher.base_url, json=malformed_payload, status=200
    )

    actual = fetcher.fetch_latest_news()

    assert actual == []


def test_fetch_historical_news_success_and_filters_urls(block_requests_library):
    fetcher = GdeltFetcher()
    mock_payload = {
        "articles": [
            {
                "url": "https://example.com/news/1",
                "title": "Historical Valid",
                "seendate": "20231024T153000Z",
                "domain": "example.com",
                "sourcecountry": "United States",
            },
            {
                "url": "https://example.com/sports/hockey",
                "title": "Historical Blacklisted",
                "seendate": "20231024T154000Z",
                "domain": "example.com",
                "sourcecountry": "United States",
            },
        ]
    }
    block_requests_library.add(
        responses.GET, fetcher.base_url, json=mock_payload, status=200
    )

    actual = fetcher.fetch_historical_news(
        start_datetime="20231024000000", end_datetime="20231024235959"
    )

    assert len(actual) == 1
    assert actual[0].title == "Historical Valid"


def test_fetch_historical_news_aborts_on_empty_whitelist(monkeypatch):
    monkeypatch.setattr(settings, "GDELT_WHITELIST", set())
    fetcher = GdeltFetcher()

    actual = fetcher.fetch_historical_news(
        start_datetime="20231024000000", end_datetime="20231024235959"
    )

    assert actual == []


def test_fetch_historical_news_handles_rate_limits(block_requests_library):
    fetcher = GdeltFetcher()
    block_requests_library.add(responses.GET, fetcher.base_url, json={}, status=429)

    with pytest.raises(ConnectionError, match="HTTP 429: Too Many Requests"):
        fetcher.fetch_historical_news(
            start_datetime="20231024000000", end_datetime="20231024235959"
        )


def test_fetch_historical_news_returns_empty_when_no_articles(block_requests_library):
    fetcher = GdeltFetcher()
    block_requests_library.add(
        responses.GET, fetcher.base_url, json={"status": "ok"}, status=200
    )

    actual = fetcher.fetch_historical_news(
        start_datetime="20231024000000", end_datetime="20231024235959"
    )

    assert actual == []


def test_fetch_historical_news_raises_connection_error_on_network_failure(
    block_requests_library,
):
    import requests

    fetcher = GdeltFetcher()
    block_requests_library.add(
        responses.GET,
        fetcher.base_url,
        body=requests.exceptions.RequestException("Network dropped"),
    )

    with pytest.raises(ConnectionError, match="Historical API connection failed"):
        fetcher.fetch_historical_news(
            start_datetime="20231024000000", end_datetime="20231024235959"
        )
