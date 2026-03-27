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
        """
        Converts GDELT's custom string into a Python datetime object.
        Falls back to default Pydantic parsing for standard formats.
        """
        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
            except ValueError:
                pass
        return value


class GdeltResponse(BaseModel):
    """Wrapper for the GDELT API response containing a list of articles."""

    articles: list[ArticleData] = []


class EntityResponse(BaseModel):
    """Represents a single extracted entity and its sentiment."""

    entity: str
    type: str
    sentiment: float


class TimelinePoint(BaseModel):
    """Represents a point on the sentiment timeline."""

    sequence_index: int
    sentiment_score: float


class KeySnippets(BaseModel):
    """The isolated snippets representing extremities in sentiment."""

    most_positive: str | None = None
    most_negative: str | None = None


class ArticleResponse(BaseModel):
    """Represents the article data returned to API."""

    id: str
    url: HttpUrl
    title: str
    seendate: datetime
    domain: str
    sourcecountry: str

    sentiment_score: float | None = None
    entities: list[EntityResponse] = []

    timeline: list[TimelinePoint] = []
    snippets: KeySnippets | None = None


class ArticleListResponse(BaseModel):
    """Paginated response wrapper for multiple articles."""

    total_results: int
    page: int
    size: int
    total_pages: int
    articles: list[ArticleResponse]
