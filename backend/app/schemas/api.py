from datetime import datetime

from pydantic import BaseModel, HttpUrl


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


class EntityLeaderboardItem(BaseModel):
    """Represents a single entity on the leaderboard."""

    entity: str
    type: str
    avg_sentiment: float
    sum_sentiment: float
    mention_count: int


class TopEntitiesResponse(BaseModel):
    """Response wrapper for multiple entities."""

    most_positive: list[EntityLeaderboardItem]
    most_negative: list[EntityLeaderboardItem]


class TrendDataPoint(BaseModel):
    """Represents a single point on the sentiment timeline chart."""

    date: str
    avg_sentiment: float
    doc_count: int


class SentimentTrendResponse(BaseModel):
    """Response wrapper for a list of trend data points."""

    trends: list[TrendDataPoint]


class DomainListResponse(BaseModel):
    """Returns a list of unique domains for the UI filter dropdown."""

    domains: list[str]


class DomainEntityStats(BaseModel):
    """Represents entity statistics by news domain."""

    domain: str
    mention_count: int
    avg_sentiment: float
    sum_sentiment: float


class EntityAnalysisResponse(BaseModel):
    """Response wrapper for entity analysis across domains."""

    entity: str
    total_mentions: int
    overall_avg_sentiment: float
    overall_sum_sentiment: float
    domains: list[DomainEntityStats]


class EntitySuggestionItem(BaseModel):
    """A single autocomplete prediction match."""

    name: str


class EntitySuggestionResponse(BaseModel):
    """Wrapper response for entity suggestions."""

    suggestions: list[EntitySuggestionItem]
