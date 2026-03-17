from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator


class ArticleData(BaseModel):
    """Represents a single article returned by the GDELT API."""

    url: HttpUrl
    title: str
    seendate: datetime
    domain: str
    sourcecountry: str

    @field_validator("seendate", mode="before")
    @classmethod
    def parse_gdelt_date(cls, value):
        """Converts GDELT's custom string into a Python datetime object."""
        if isinstance(value, str):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
        return value


class GdeltResponse(BaseModel):
    """Wrapper for the GDELT API response containing a list of articles."""

    articles: list[ArticleData] = []
