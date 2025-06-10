import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def test_client(monkeypatch):
    # Mock all required environment variables
    monkeypatch.setenv("NOTION_API_KEY", "test_notion_api_key")
    monkeypatch.setenv("NOTION_DATABASE_IDS", "db1,db2")
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "test_db")
    monkeypatch.setenv("MONGODB_COLLECTION", "test_collection")
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_api_key")
    monkeypatch.setenv("GOOGLE_MODEL", "test_google_model")
    monkeypatch.setenv("EMBEDDING_MODEL", "test_embedding_model")
    monkeypatch.setenv("MAX_CHUNK_TOKENS", "500")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "50")
    monkeypatch.setenv("MAX_CONTEXT_CHUNKS", "5")
    monkeypatch.setenv("MIN_SIMILARITY_SCORE", "0.7")
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")
    monkeypatch.setenv("API_SECRET_KEY", "test_api_secret_key")
    from main import app
    client = TestClient(app)
    yield client

def test_root_endpoint(test_client):
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Cloud Brain API is running"}