from unittest.mock import AsyncMock


def test_get_domains_success(client, mock_search_client):
    mock_search_client.get_domains = AsyncMock(
        return_value={"domains": ["cnn.com", "bbc.co.uk"]}
    )

    response = client.get("/api/v1/metadata/domains")

    mock_search_client.get_domains.assert_awaited_once()
    assert response.status_code == 200
    assert "cnn.com" in response.json()["domains"]


def test_get_domains_503_connection_error(client, mock_search_client):
    mock_search_client.get_domains = AsyncMock(side_effect=ConnectionError())

    response = client.get("/api/v1/metadata/domains")

    assert response.status_code == 503
    assert response.json()["detail"] == "Search service is temporarily unavailable."


def test_get_domains_500_runtime_error(client, mock_search_client):
    mock_search_client.get_domains = AsyncMock(side_effect=RuntimeError())

    response = client.get("/api/v1/metadata/domains")

    assert response.status_code == 500
    assert response.json()["detail"] == "An internal search error occurred."
