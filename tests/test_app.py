"""
Simple tests for the Cloud Brain API
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

@pytest.fixture(scope="module")
def test_client():
    # Patch environment variables before importing the app
    with patch.dict(os.environ, {
        "NOTION_API_KEY": "test_key",
        "API_SECRET_KEY": "test_api_key"
    }):
        from main import app
        client = TestClient(app)
        yield client

def test_root_endpoint(test_client):
    """Test the root endpoint"""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Cloud Brain API is running"}

def test_health_check_success(test_client):
    """Test health check when Notion API is accessible"""
    with patch('main.notion') as mock_notion:
        mock_notion.users.me.return_value = {"id": "test_user"}
        response = test_client.get("/health", headers={"X-API-KEY": "test_api_key"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["notion_api"] == "connected"

def test_health_check_failure(test_client):
    """Test health check when Notion API is not accessible"""
    with patch('main.notion') as mock_notion:
        mock_notion.users.me.side_effect = Exception("API Error")
        response = test_client.get("/health", headers={"X-API-KEY": "test_api_key"})
        assert response.status_code == 503

def test_notion_utils_import():
    """Test that notion_utils can be imported"""
    from utils.notion_utils import NotionUtils
    assert NotionUtils is not None

if __name__ == "__main__":
    pytest.main([__file__])