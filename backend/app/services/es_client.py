import hashlib
import logging

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ConnectionError as ESConnectionError

from app.core.config import settings
from app.schemas.article import ArticleData

logger = logging.getLogger(__name__)


class ElasticClient:
    """Wrapper for Elasticsearch operations."""

    def __init__(self):
        self.client = Elasticsearch(settings.ELASTICSEARCH_URL)
        self.index_name = settings.ELASTIC_INDEX_NAME

    def create_index(self):
        """Creates the index with specific mappings if it does not exist."""
        if self.client.indices.exists(index=self.index_name):
            return

        index_mappings = {
            "properties": {
                "url": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "english"},
                "domain": {"type": "keyword"},
                "sourcecountry": {"type": "keyword"},
                "seendate": {"type": "date"},
                "content": {"type": "text", "analyzer": "english"},
                "sentiment_score": {"type": "float"},
                "entities": {
                    "type": "nested",
                    "properties": {
                        "entity": {"type": "keyword"},
                        "type": {"type": "keyword"},
                        "sentiment": {"type": "float"},
                    },
                },
                "sentences": {
                    "type": "nested",
                    "properties": {
                        "sequence_index": {"type": "integer"},
                        "text": {"type": "text", "analyzer": "english"},
                        "sentiment_score": {"type": "float"},
                    },
                },
            }
        }

        try:
            self.client.indices.create(index=self.index_name, mappings=index_mappings)
            logger.info(f"Created Elasticsearch index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to create index {self.index_name}: {e}")

    def index_article(self, article: ArticleData, text: str) -> bool:
        """
        Indexes an article. Hashes the URL to create a safe document ID.
        """
        url_str = str(article.url)

        # Hash to prevent character limit issues in the _id field
        doc_id = self.get_doc_id(url_str)

        document = {
            "url": url_str,
            "title": article.title,
            "domain": article.domain,
            "sourcecountry": article.sourcecountry,
            "seendate": article.seendate,
            "content": text,
            "sentiment_score": None,
            "entities": [],
            "sentences": [],
        }

        try:
            self.client.index(index=self.index_name, id=doc_id, document=document)
            logger.debug(f"Successfully indexed article: {url_str}")
            return True
        except ESConnectionError as e:
            logger.error(
                f"Elasticsearch connection error while indexing {url_str}: {e}"
            )
            raise ConnectionError(f"Elasticsearch connection failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error indexing {url_str}: {e}")
            return False

    def article_exists(self, url: str) -> bool:
        """Checks if an article is already indexed based on its URL hash."""
        doc_id = self.get_doc_id(url)
        try:
            return self.client.exists(index=self.index_name, id=doc_id)
        except Exception as e:
            logger.warning(f"Failed to check existence for {url}: {e}")
            return False

    def get_doc_id(self, url: str) -> str:
        """Generates the Elasticsearch document ID (SHA-256 hash) from a URL"""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def update_article_nlp(self, doc_id: str, nlp_payload: dict) -> bool:
        """
        Updates an existing article document with the computed NLP data (sentences, entities, sentiment).
        """
        try:
            response = self.client.update(
                index=self.index_name,
                id=doc_id,
                doc={
                    "sentences": nlp_payload.get("sentences", []),
                    "entities": nlp_payload.get("entities", []),
                    "sentiment_score": nlp_payload.get("sentiment_score"),
                },
            )
            # "updated" means it changed, "noop" means the data was already exactly the same
            if response["result"] in ["updated", "noop"]:
                logger.info(f"Successfully updated document {doc_id} with NLP payload.")
                return True
            return False

        except Exception as e:
            error_name = type(e).__name__
            logger.error(
                f"Failed to update document {doc_id}. Error type: {error_name}"
            )
            return False

    def get_missing_scored_days(self, days_back: int = 30) -> list[str]:
        """Finds days within the last `days_back` that have zero scored articles."""
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        # Exclude today
        end_date = datetime.now(timezone.utc) - timedelta(days=1)
        start_date = now - timedelta(days=days_back)

        query = {
            "range": {
                "seendate": {
                    "gte": start_date.strftime("%Y-%m-%d"),
                    "lte": now.strftime("%Y-%m-%d"),
                }
            }
        }

        aggs = {
            "daily_articles": {
                "date_histogram": {
                    "field": "seendate",
                    "calendar_interval": "1d",
                    "format": "yyyyMMdd",
                    "min_doc_count": 0,
                    "extended_bounds": {
                        "min": start_date.strftime("%Y%m%d"),
                        "max": end_date.strftime("%Y%m%d"),
                    },
                },
                "aggs": {
                    "scored_docs": {"filter": {"exists": {"field": "sentiment_score"}}}
                },
            }
        }

        try:
            response = self.client.search(
                index=self.index_name, size=0, query=query, aggs=aggs
            )

            buckets = (
                response.get("aggregations", {})
                .get("daily_articles", {})
                .get("buckets", [])
            )
            missing_days = []

            for b in buckets:
                if b.get("scored_docs", {}).get("doc_count", 0) == 0:
                    missing_days.append(b["key_as_string"])
            # most recent days first
            missing_days.reverse()
            return missing_days

        except Exception as e:
            logger.error(f"Failed to find missing days: {e}")
            return []
