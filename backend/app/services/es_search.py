import logging
import math

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError
from elasticsearch.exceptions import NotFoundError

from app.core.config import settings
from app.schemas.api import (
    ArticleListResponse,
    ArticleResponse,
    DomainListResponse,
    EntityLeaderboardItem,
    KeySnippets,
    SentimentTrendResponse,
    TimelinePoint,
    TopEntitiesResponse,
    TrendDataPoint,
)

logger = logging.getLogger(__name__)


class AsyncSearchClient:
    """Asynchronous wrapper for Elasticsearch API operations."""

    def __init__(self):
        self.client = AsyncElasticsearch(settings.ELASTICSEARCH_URL)
        self.index_name = settings.ELASTIC_INDEX_NAME

    async def close(self):
        """Closes the async connection pool. Called during app shutdown."""
        await self.client.close()

    async def search_articles(
        self,
        query_str: str | None = None,
        domain: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> ArticleListResponse | None:
        """Executes a paginated search query and returns ArticleListResponse schema."""
        from_offset = (page - 1) * size

        must_clauses = []
        filter_clauses = []

        if query_str:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query_str,
                        "fields": ["title^2", "content"],  # Boost title relevance by 2x
                    }
                }
            )
        else:
            # If no query string, match all documents
            must_clauses.append({"match_all": {}})

        if domain:
            # Exact match filtering
            filter_clauses.append({"term": {"domain": domain}})

        try:
            response = await self.client.search(
                index=self.index_name,
                query={"bool": {"must": must_clauses, "filter": filter_clauses}},
                sort=[{"seendate": {"order": "desc"}}],
                from_=from_offset,
                size=size,
            )
            return self._format_response(response, page, size)

        except ESConnectionError as e:
            logger.error(f"Async Elasticsearch connection failed during search: {e}")
            raise ConnectionError("Database connection failed") from e
        except Exception as e:
            logger.error(f"Unexpected error executing search: {e}")
            raise RuntimeError("Internal search execution failed") from e

    def _format_response(
        self, es_response: dict, page: int, size: int
    ) -> ArticleListResponse:
        """Transforms the raw Elasticsearch JSON into the validated API schema."""
        hits_data = es_response.get("hits", {})

        total_results = hits_data.get("total", {}).get("value", 0)
        total_pages = math.ceil(total_results / size) if size > 0 else 0

        articles = []
        for hit in hits_data.get("hits", []):
            source = hit["_source"]
            doc_id = hit["_id"]

            # Transform Sentences into Timeline and Snippets
            timeline = []
            snippets = KeySnippets()
            raw_sentences = source.get("sentences", [])

            if raw_sentences:
                timeline = [
                    TimelinePoint(
                        sequence_index=s.get("sequence_index", 0),
                        sentiment_score=s.get("sentiment_score", 0.0),
                    )
                    for s in raw_sentences
                    if s.get("sentiment_score") is not None
                ]

                scored_sentences = [
                    s for s in raw_sentences if s.get("sentiment_score") is not None
                ]
                if scored_sentences:
                    most_pos = max(scored_sentences, key=lambda x: x["sentiment_score"])
                    most_neg = min(scored_sentences, key=lambda x: x["sentiment_score"])

                    snippets = KeySnippets(
                        most_positive=most_pos.get("text"),
                        most_negative=most_neg.get("text"),
                    )

            # Included default values in case of malfunctions
            article = ArticleResponse(
                id=doc_id,
                url=source.get("url"),
                title=source.get("title", "Untitled"),
                seendate=source.get("seendate"),
                domain=source.get("domain", "Unknown"),
                sourcecountry=source.get("sourcecountry", "Unknown"),
                sentiment_score=source.get("sentiment_score"),
                entities=source.get("entities", []),
                timeline=timeline,
                snippets=snippets,
            )
            articles.append(article)

        return ArticleListResponse(
            total_results=total_results,
            page=page,
            size=size,
            total_pages=total_pages,
            articles=articles,
        )

    async def get_article(self, article_id: str) -> ArticleResponse | None:
        """Fetches a single article by ID and returns the schema."""
        try:
            response = await self.client.get(index=self.index_name, id=article_id)
            source = response["_source"]
            doc_id = response["_id"]

            timeline = []
            snippets = KeySnippets()
            raw_sentences = source.get("sentences", [])

            if raw_sentences:
                timeline = [
                    TimelinePoint(
                        sequence_index=s.get("sequence_index", 0),
                        sentiment_score=s.get("sentiment_score", 0.0),
                    )
                    for s in raw_sentences
                    if s.get("sentiment_score") is not None
                ]

                scored_sentences = [
                    s for s in raw_sentences if s.get("sentiment_score") is not None
                ]
                if scored_sentences:
                    most_pos = max(scored_sentences, key=lambda x: x["sentiment_score"])
                    most_neg = min(scored_sentences, key=lambda x: x["sentiment_score"])

                    snippets = KeySnippets(
                        most_positive=most_pos.get("text"),
                        most_negative=most_neg.get("text"),
                    )

            return ArticleResponse(
                id=doc_id,
                url=source.get("url"),
                title=source.get("title", "Untitled"),
                seendate=source.get("seendate"),
                domain=source.get("domain", "Unknown"),
                sourcecountry=source.get("sourcecountry", "Unknown"),
                sentiment_score=source.get("sentiment_score"),
                entities=source.get("entities", []),
                timeline=timeline,
                snippets=snippets,
            )
        except NotFoundError:
            return None
        except ESConnectionError as e:
            logger.error(
                f"Elasticsearch connection error fetching article {article_id}: {e}"
            )
            raise ConnectionError("Database connection failed") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching article {article_id}: {e}")
            raise RuntimeError("Internal search execution failed") from e

    async def get_sentiment_trend(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        interval: str = "day",
        domain: str | None = None,
    ) -> list[dict]:
        """Aggregates average sentiment over time intervals."""

        filter_clauses = []
        if domain:
            filter_clauses.append({"term": {"domain": domain}})

        date_range = {}
        if start_date:
            date_range["gte"] = start_date
        if end_date:
            date_range["lte"] = end_date
        if date_range:
            filter_clauses.append({"range": {"seendate": date_range}})

        query = (
            {"bool": {"filter": filter_clauses}}
            if filter_clauses
            else {"match_all": {}}
        )

        aggs = {
            "trend": {
                "date_histogram": {
                    "field": "seendate",
                    "calendar_interval": interval,
                    "format": "yyyy-MM-dd",
                },
                "aggs": {"avg_sentiment": {"avg": {"field": "sentiment_score"}}},
            }
        }

        try:
            response = await self.client.search(
                index=self.index_name,
                size=0,
                query=query,
                aggs=aggs,
            )

            buckets = (
                response.get("aggregations", {}).get("trend", {}).get("buckets", [])
            )

            trend_points = []
            for b in buckets:
                val = b.get("avg_sentiment", {}).get("value")
                point = TrendDataPoint(
                    date=b.get("key_as_string", b["key"]),
                    avg_sentiment=round(val, 4) if val is not None else 0.0,
                    doc_count=b["doc_count"],
                )
                trend_points.append(point)
            return SentimentTrendResponse(trends=trend_points).model_dump()

        except Exception as e:
            logger.error(f"Error fetching sentiment trend: {e}")
            raise RuntimeError("Failed to fetch sentiment trend") from e

    async def get_top_entities(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        domain: str | None = None,
        min_mentions: int = 5,
    ) -> dict:
        """Finds the most impactful positive and negative entities."""

        filter_clauses = []
        date_range = {}

        if domain:
            filter_clauses.append({"term": {"domain": domain}})

        if start_date:
            date_range["gte"] = start_date
        if end_date:
            date_range["lte"] = end_date
        if date_range:
            filter_clauses.append({"range": {"seendate": date_range}})

        query = (
            {"bool": {"filter": filter_clauses}}
            if filter_clauses
            else {"match_all": {}}
        )

        aggs = {
            "nested_entities": {
                "nested": {"path": "entities"},
                "aggs": {
                    "most_positive": {
                        "terms": {
                            "field": "entities.entity",
                            "size": 10,
                            "shard_size": 1000,
                            "min_doc_count": min_mentions,
                            "order": {"sum_sentiment": "desc"},
                        },
                        "aggs": {
                            "sum_sentiment": {"sum": {"field": "entities.sentiment"}},
                            "avg_sentiment": {"avg": {"field": "entities.sentiment"}},
                            "entity_type": {
                                "terms": {"field": "entities.type", "size": 1}
                            },
                        },
                    },
                    "most_negative": {
                        "terms": {
                            "field": "entities.entity",
                            "size": 10,
                            "shard_size": 1000,
                            "min_doc_count": min_mentions,
                            "order": {"sum_sentiment": "asc"},
                        },
                        "aggs": {
                            "sum_sentiment": {"sum": {"field": "entities.sentiment"}},
                            "avg_sentiment": {"avg": {"field": "entities.sentiment"}},
                            "entity_type": {
                                "terms": {"field": "entities.type", "size": 1}
                            },
                        },
                    },
                },
            }
        }

        try:
            response = await self.client.search(
                index=self.index_name,
                size=0,
                query=query,
                aggs=aggs,
            )

            nested_entities = response.get("aggregations", {}).get(
                "nested_entities", {}
            )
            positive_buckets = nested_entities.get("most_positive", {}).get(
                "buckets", []
            )
            negative_buckets = nested_entities.get("most_negative", {}).get(
                "buckets", []
            )

            def format_bucket(bucket: dict) -> EntityLeaderboardItem:
                avg_sentiment = bucket.get("avg_sentiment", {}).get("value")
                sum_sentiment = bucket.get("sum_sentiment", {}).get("value")

                type_buckets = bucket.get("entity_type", {}).get("buckets", [])
                ent_type = (
                    type_buckets[0].get("key", "Unknown") if type_buckets else "Unknown"
                )

                return EntityLeaderboardItem(
                    entity=bucket.get("key"),
                    type=ent_type,
                    avg_sentiment=round(avg_sentiment, 4)
                    if avg_sentiment is not None
                    else 0.0,
                    sum_sentiment=round(sum_sentiment, 4)
                    if sum_sentiment is not None
                    else 0.0,
                    mention_count=bucket.get("doc_count", 0),
                )

            return TopEntitiesResponse(
                most_positive=[format_bucket(b) for b in positive_buckets],
                most_negative=[format_bucket(b) for b in negative_buckets],
            ).model_dump()

        except ESConnectionError as e:
            logger.error(f"Elasticsearch connection error fetching top entities: {e}")
            raise ConnectionError("Database connection failed") from e
        except Exception as e:
            logger.error(f"Error fetching top entities: {e}")
            raise RuntimeError("Failed to fetch top entities") from e

    async def get_domains(self) -> dict:
        """Returns a list of stored domains."""

        aggs = {
            "unique_domains": {
                "terms": {
                    "field": "domain",
                    "size": 100,
                    "order": {"_count": "desc"},
                }
            }
        }
        try:
            response = await self.client.search(
                index=self.index_name, size=0, aggs=aggs
            )
            buckets = (
                response.get("aggregations", {})
                .get("unique_domains", {})
                .get("buckets", [])
            )

            domains = [b["key"] for b in buckets]
            return DomainListResponse(domains=domains).model_dump()

        except Exception as e:
            logger.error(f"Error fetching domains: {e}")
            raise RuntimeError("Failed to fetch domains") from e
