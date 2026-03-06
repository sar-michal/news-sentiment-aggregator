import logging
import requests
from typing import List
from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator

from app.core.config import settings

__all__ = ["GdeltFetcher", "ArticleData"]

logger = logging.getLogger(__name__)

# --- Data Models ---
class ArticleData(BaseModel):
    """Represents a single article returned by the GDELT API."""
    url: HttpUrl
    title: str
    seendate: datetime
    domain: str
    sourcecountry: str

    @field_validator('seendate', mode='before')
    @classmethod
    def parse_gdelt_date(cls, value):
        """Converts GDELT's custom string into a Python datetime object."""
        if isinstance(value, str):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        return value

class GdeltResponse(BaseModel):
    """Wrapper for the GDELT API response containing a list of articles."""
    articles: List[ArticleData] = []

# --- Service Class ---
class GdeltFetcher:
    """Service to communicate with the GDELT 2.0 DOC API."""
    def __init__(self):
        self.base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
        self.whitelist = settings.GDELT_WHITELIST

    def fetch_latest_news(self, max_records: int = 50) -> List[ArticleData]:
        """Fetches the latest English news from whitelisted domains."""
        if not self.whitelist:
            logger.warning("GDELT whitelist is empty. Skipping fetch.")
            return []

        domain_query = " OR ".join([f"domainis:{domain}" for domain in self.whitelist])
        
        params = {
            "query": f"sourcelang:eng ({domain_query})",
            "mode": "artlist",
            "format": "json",
            "maxrecords": max_records,
            "sort": "datedesc"
        }

        try:
            logger.info(f"Fetching data from GDELT (Max: {max_records})...")
            response = requests.get(self.base_url, params=params, timeout=15)
            
            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("GDELT Rate Limit hit (HTTP 429). Skipping this cycle.")
                return []
                
            response.raise_for_status() 
            data = response.json()
            
            if "articles" not in data:
                logger.info("No articles found.")
                return []
                
            # Validate using Pydantic
            parsed_data = GdeltResponse(**data)
            
            # Post-fetch validation
            valid_articles = [
                art for art in parsed_data.articles 
                if art.domain in self.whitelist
            ]
            
            logger.info(f"Successfully validated {len(valid_articles)} articles.")
            return valid_articles

        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to GDELT: {e}")
            return []