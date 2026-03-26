import pytest
import responses
from app.core.config import Environment, settings
from app.main import app
from app.workers.celery_app import celery
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Provides a test client for FastAPI routes."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def celery_eager():
    """
    Forces Celery to execute tasks synchronously during tests.
    It also makes it store results locally.
    """
    celery.conf.update(task_always_eager=True, task_store_eager_result=True)


@pytest.fixture(autouse=True)
def override_settings(monkeypatch: pytest.MonkeyPatch):
    """
    Overrides application settings with test values.
    Uses monkeypatch to isolate test settings for each test.
    """
    monkeypatch.setattr(settings, "GDELT_WHITELIST", {"test-domain.com", "example.com"})
    monkeypatch.setattr(settings, "URL_BLACKLIST", ("/video/", "/sports/"))
    monkeypatch.setattr(settings, "ENVIRONMENT", Environment.TESTING)

    yield settings


@pytest.fixture(autouse=True)
def block_requests_library():
    """
    Prevents tests from making unmocked external HTTP requests via the `requests` library.
    """
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture(autouse=True)
def block_trafilatura_scraping(monkeypatch: pytest.MonkeyPatch):
    """
    Mocks Trafilatura's top-level fetch_url to prevent outbound web scraping.
    """
    import trafilatura

    def mocked_fetch_url(*args, **kwargs):
        raise RuntimeError(
            "Trafilatura tried to make a network request during a test. Mock it first."
        )

    monkeypatch.setattr(trafilatura, "fetch_url", mocked_fetch_url)
    yield
