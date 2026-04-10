import logging
import math

from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from app.core.config import settings
from app.schemas.article import (
    ArticleListResponse,
    ArticleResponse,
    KeySnippets,
    TimelinePoint,
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
