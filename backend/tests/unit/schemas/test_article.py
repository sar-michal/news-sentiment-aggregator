from datetime import datetime

import pytest
from app.schemas.article import ArticleData
from pydantic import ValidationError


def test_valid_data_initializes_fields_correctly():
    mock_data = {
        "url": "https://example.com/news/123",
        "title": "A Very Important Event",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "US",
    }

    article = ArticleData(**mock_data)

    assert str(article.url) == "https://example.com/news/123"
    assert article.title == "A Very Important Event"
    assert article.seendate == datetime(2023, 10, 24, 15, 30, 0)


def test_invalid_url_raises_validation_error():
    mock_data = {
        "url": "not-a-real-url",
        "title": "A Very Important Event",
        "seendate": "20231024T153000Z",
        "domain": "example.com",
        "sourcecountry": "US",
    }

    with pytest.raises(ValidationError, match="(?i)url"):
        ArticleData(**mock_data)
