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
        doc_id = hashlib.sha256(url_str.encode("utf-8")).hexdigest()

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
