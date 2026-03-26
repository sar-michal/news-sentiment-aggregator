from enum import StrEnum

from pydantic_settings import BaseSettings


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    REDIS_URL: str = "redis://redis:6379/0"
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTIC_INDEX_NAME: str = "news_articles"
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT

    # Whitelist for domain filtering in GDELT queries
    GDELT_WHITELIST: set[str] = {
        "reuters.com",
        "apnews.com",
        "bbc.co.uk",
        "bbc.com",
        "aljazeera.com",
        "dw.com",
        "theguardian.com",
        "npr.org",
        "cnn.com",
        "cnbc.com",
    }

    # Blacklist for URL path filtering
    URL_BLACKLIST: tuple[str, ...] = {
        # 1. Non-English / Regional
        "/pidgin/",
        "/mundo/",
        "/afrique/",
        "/espanol/",
        # 2. Live Blogs (Fragmented text)
        "/live/",
        "/liveblog/",
        "/live-news/",
        "/live-",
        # 3. Multimedia / Interactive (No prose)
        "/interactive/",
        "/video/",
        "/gallery/",
        "/audio/",
        "/sounds/",
        "/photos/",
        "/transcripts/",
        "/podcasts/"
        # 4. Sports (Aggressive vocabulary skews geopolitical sentiment)
        "/sport/",
        "/sports/",
        # 5. Entertainment & Arts
        "/film/",
        "/music/",
        "/tv-and-radio/",
        "/books/",
        "/games/",
        "/entertainment/",
        "/arts/",
        "/culture/",
        # 6. Lifestyle / Fluff / Affiliate Marketing
        "/lifeandstyle/",
        "/food/",
        "/style/",
        "/travel/",
        "/health/",
        "/tiny-happy-people/",
        "/select/",
        "/wellness/",
        "/recipes/",
        "/coupons/",
        # 7. Opinion Pieces & Editorials (Highly subjective/biased)
        "/commentisfree/",
        "/opinion/",
        "/opinions/",
        "/editorials/"
        # 8. Administrative / Housekeeping
        "/corrections-and-clarifications",
    }


# Module level singleton
settings = Settings()
