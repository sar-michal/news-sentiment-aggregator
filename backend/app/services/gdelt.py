import logging
from urllib.parse import urlsplit

import requests
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.article import ArticleData, GdeltResponse

logger = logging.getLogger(__name__)


# --- Service Class ---
class GdeltFetcher:
    """Service to communicate with the GDELT 2.0 DOC API."""

    def __init__(self):
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.whitelist = settings.GDELT_WHITELIST
        self.url_blacklist = settings.URL_BLACKLIST

    def _is_valid_url(self, url: str) -> bool:
        """Returns True if the URL path does not contain blacklisted elements."""
        # Split to only check path
        path = urlsplit(str(url)).path.lower()
        if any(bad_path in path for bad_path in self.url_blacklist):
            return False
        return True

    def fetch_latest_news(
        self, max_records: int = 50, timespan: str | None = None
    ) -> list[ArticleData]:
        """Fetches the latest English news from whitelisted domains.

        Args:
            max_records: The maximum number of articles to return.
            timespan: Filters articles by a rolling time window. Minimum of 15min.
                Format rules:
                - Minutes: a number followed by "min" (e.g., "15min")
                - Hours: a number followed by "h" (e.g., "24h")
                - Days: a number followed by "d" (e.g., "7d")
                - Weeks: a number followed by "w" (e.g., "1w")
                - Months: a number followed by "m" (e.g., "3m")
        """
        if not self.whitelist:
            logger.warning("GDELT whitelist is empty. Skipping fetch.")
            return []

        domain_query = " OR ".join([f"domainis:{domain}" for domain in self.whitelist])

        params = {
            "query": f"sourcelang:eng ({domain_query})",
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
            "sort": "datedesc",
        }

        if timespan:
            params["timespan"] = timespan

        try:
            logger.info(f"Fetching data from GDELT (Max: {max_records})...")

            headers = {"User-Agent": "NewsSentimentThesisBot"}
            response = requests.get(
                self.base_url, params=params, headers=headers, timeout=20
            )

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning(
                    "GDELT Rate Limit hit (HTTP 429). Raising exception for Celery retry."
                )
                raise ConnectionError("HTTP 429: Too Many Requests")

            response.raise_for_status()
            data = response.json()

            if "articles" not in data:
                logger.info("No articles found.")
                return []

            try:
                # Validate using Pydantic
                parsed_data = GdeltResponse(**data)
            except ValidationError as e:
                logger.error(f"Data validation failed due to schema change: {e}")
                return []

            # Post-fetch validation
            valid_articles = [
                art
                for art in parsed_data.articles
                if art.domain in self.whitelist and self._is_valid_url(art.url)
            ]

            logger.info(f"Successfully validated {len(valid_articles)} articles.")
            return valid_articles

        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            clean_url = e.request.url.split("?")[0] if e.request else self.base_url

            logger.error(f"Error connecting to GDELT: {error_type} at {clean_url}")
            raise ConnectionError(f"GDELT API connection failed: {error_type}") from e

    def fetch_historical_news(
        self, start_datetime: str, end_datetime: str, max_records: int = 250
    ) -> list[ArticleData]:
        """
        Fetches historical English news using STARTDATETIME and ENDDATETIME.
        Format must be: YYYYMMDDHHMMSS
        """
        if not self.whitelist:
            logger.warning("GDELT whitelist is empty. Skipping historical fetch.")
            return []

        domain_query = " OR ".join([f"domainis:{domain}" for domain in self.whitelist])

        params = {
            "query": f"sourcelang:eng ({domain_query})",
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
            "sort": "datedesc",
            "STARTDATETIME": start_datetime,
            "ENDDATETIME": end_datetime,
        }

        try:
            logger.info(
                f"Fetching historical GDELT data ({start_datetime} to {end_datetime})..."
            )
            headers = {"User-Agent": "NewsSentimentThesisBot"}
            response = requests.get(
                self.base_url, params=params, headers=headers, timeout=20
            )

            if response.status_code == 429:
                logger.warning("GDELT Rate Limit hit during historical fetch.")
                raise ConnectionError("HTTP 429: Too Many Requests")

            response.raise_for_status()
            data = response.json()

            if "articles" not in data:
                logger.info(f"No historical articles found for {start_datetime}.")
                return []

            try:
                parsed_data = GdeltResponse(**data)
            except ValidationError as e:
                logger.error(f"Validation failed for historical data: {e}")
                return []

            valid_articles = [
                art
                for art in parsed_data.articles
                if art.domain in self.whitelist and self._is_valid_url(art.url)
            ]

            logger.info(f"Validated {len(valid_articles)} historical articles.")
            return valid_articles

        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            clean_url = e.request.url.split("?")[0] if e.request else self.base_url
            logger.error(f"Error fetching historical data: {error_type} at {clean_url}")
            raise ConnectionError(
                f"Historical API connection failed: {error_type}"
            ) from e
