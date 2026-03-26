import urllib.request
from unittest.mock import MagicMock
from urllib.error import URLError
from urllib.robotparser import RobotFileParser

import pytest
import trafilatura
from app.services.scraper import NewsScraper


def test_scrape_article_aborts_when_robots_txt_forbids(monkeypatch):
    scraper = NewsScraper()
    monkeypatch.setattr(scraper, "can_fetch", lambda url: False)

    actual = scraper.scrape_article("https://example.com/forbidden")

    assert actual is None


def test_scrape_article_raises_error_when_trafilatura_download_fails(monkeypatch):
    scraper = NewsScraper()
    monkeypatch.setattr(scraper, "can_fetch", lambda url: True)
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: None)

    with pytest.raises(ConnectionError, match="Trafilatura failed to download"):
        scraper.scrape_article("https://example.com/bad-server")


def test_scrape_article_returns_none_when_extraction_fails(monkeypatch):
    scraper = NewsScraper()
    monkeypatch.setattr(scraper, "can_fetch", lambda url: True)
    monkeypatch.setattr(
        trafilatura, "fetch_url", lambda url: "<html>No article here</html>"
    )
    monkeypatch.setattr(trafilatura, "extract", lambda html, **kwargs: None)

    actual = scraper.scrape_article("https://example.com/empty-page")

    assert actual is None


def test_scrape_article_returns_extracted_text_on_success(monkeypatch):
    scraper = NewsScraper()
    monkeypatch.setattr(scraper, "can_fetch", lambda url: True)
    monkeypatch.setattr(trafilatura, "fetch_url", lambda url: "<html>raw data</html>")
    monkeypatch.setattr(
        trafilatura, "extract", lambda html, **kwargs: "Cleaned article text."
    )

    actual = scraper.scrape_article("https://example.com/good-article")

    assert actual == "Cleaned article text."


@pytest.mark.parametrize(
    "is_allowed_by_parser, expected",
    [
        (True, True),
        (False, False),
    ],
)
def test_can_fetch_evaluates_rules_and_caches_parser(
    monkeypatch, is_allowed_by_parser, expected
):
    scraper = NewsScraper()
    domain = "https://example.com"
    target_url = f"{domain}/some/article"

    mock_response = MagicMock()
    mock_response.read.return_value = b"User-agent: *\nAllow: /"

    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_response
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    monkeypatch.setattr(
        RobotFileParser, "can_fetch", lambda self, agent, url: is_allowed_by_parser
    )

    assert len(scraper._robot_parsers) == 0

    actual = scraper.can_fetch(target_url)

    assert actual is expected
    assert len(scraper._robot_parsers) == 1
    assert domain in scraper._robot_parsers
    mock_urlopen.assert_called_once()

    scraper.can_fetch(f"{domain}/another/article")
    assert len(scraper._robot_parsers) == 1
    mock_urlopen.assert_called_once()


def test_get_robot_parser_handles_exceptions_gracefully(monkeypatch):
    scraper = NewsScraper()
    domain_url = "https://example.com"

    mock_urlopen = MagicMock()
    mock_urlopen.side_effect = URLError("Simulated network failure")
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)

    actual_parser = scraper._get_robot_parser(domain_url)

    assert isinstance(actual_parser, RobotFileParser)
    assert domain_url in scraper._robot_parsers
