from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    
    GDELT_WHITELIST: set[str] = {
        "reuters.com", "apnews.com", "bbc.co.uk", "bbc.com", 
        "aljazeera.com", "dw.com", "theguardian.com", "npr.org", 
        "cnn.com", "cnbc.com"
    }
# Module level singleton
settings = Settings()