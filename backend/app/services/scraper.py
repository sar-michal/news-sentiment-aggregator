import logging
import socket
import urllib.request
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import trafilatura

logger = logging.getLogger(__name__)


class NewsScraper:
    """Service to download and extract article text while respecting robots.txt."""

    def __init__(self, user_agent: str = "NewsSentimentThesisBot"):
        self.user_agent = user_agent
        # Dictionary to cache robots.txt parsers
        self._robot_parsers = {}

    def _get_robot_parser(self, domain_url: str) -> RobotFileParser:
        """Fetches and caches the robots.txt for a given domain."""
        if domain_url not in self._robot_parsers:
            robots_url = f"{domain_url}/robots.txt"
            rp = RobotFileParser()
            rp.set_url(robots_url)

            req = urllib.request.Request(
                robots_url, data=None, headers={"User-Agent": self.user_agent}
            )
            try:
                with urllib.request.urlopen(req, timeout=5) as response:
                    lines = (
                        response.read().decode("utf-8", errors="ignore").splitlines()
                    )
                    rp.parse(lines)
                logger.debug(f"Fetched robots.txt for {domain_url}")
            except (URLError, TimeoutError, socket.timeout) as e:
                logger.warning(
                    f"Could not fetch robots.txt for {domain_url}: {e}. Defaulting to open."
                )
                rp.parse(["User-agent: *", "Allow: /"])
            self._robot_parsers[domain_url] = rp
        return self._robot_parsers[domain_url]

    def can_fetch(self, url: str) -> bool:
        """Checks if user agent is allowed to scrape the URL."""
        parsed_url = urlsplit(url)
        domain_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

        rp = self._get_robot_parser(domain_url)
        return rp.can_fetch(self.user_agent, url)

    def scrape_article(self, url: str) -> str | None:
        """
        Validates permission, downloads the HTML, and extracts the main text.
        Returns the text if successful, or None if failed/forbidden.
        """
        if not self.can_fetch(url):
            logger.warning(f"Scraping forbidden by robots.txt for URL: {url}")
            return None

        logger.info(f"Downloading HTML from: {url}")

        downloaded_html = trafilatura.fetch_url(url)
        if downloaded_html is None:
            logger.error(f"Failed to download HTML: {url}")
            raise ConnectionError(f"Trafilatura failed to download HTML from: {url}")

        text = trafilatura.extract(
            downloaded_html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            no_fallback=False,
            deduplicate=True,
        )

        if not text:
            logger.error(f"Trafilatura could not extract useful text from: {url}")
            return None

        return text
