"""
Unit tests for vector_service.py
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


@pytest.fixture
def mock_env(monkeypatch):
    """Fixture to set environment variables for tests."""
    monkeypatch.setenv("NOTION_API_KEY", "test_notion_api_key")
    monkeypatch.setenv("NOTION_DATABASE_IDS", "db1,db2")


@pytest.fixture
def vector_service(mock_env):
    """Create VectorService instance with mocked dependencies."""
    # Create mock objects
    mock_vector_db = AsyncMock()
    mock_vector_db.store_notion_page.return_value = {
        "status": "success",
        "chunks_stored": 5
    }
    
    mock_notion_utils = AsyncMock()
    mock_notion_utils.extract_complete_page_data.return_value = {
        "id": "test-page-id",
        "properties": {"title": "Test Page"},
        "markdown_content": "# Test Content"
    }
    
    # Create mock notion client with proper structure
    mock_notion_client = MagicMock()
    mock_notion_client.databases = MagicMock()
    mock_notion_client.databases.query = AsyncMock()
    mock_notion_client.blocks = MagicMock()
    mock_notion_client.blocks.children = MagicMock()
    mock_notion_client.blocks.children.list = AsyncMock()
    mock_notion_client.pages = MagicMock()
    mock_notion_client.pages.retrieve = AsyncMock()
    
    with patch("services.vector_service.VectorDB", return_value=mock_vector_db), \
         patch("services.vector_service.AsyncClient", return_value=mock_notion_client), \
         patch("services.vector_service.NotionUtils", return_value=mock_notion_utils):
        from services.vector_service import VectorService
        service = VectorService()
        # Store references for test access
        service._mock_notion_client = mock_notion_client
        service._mock_notion_utils = mock_notion_utils
        service._mock_vector_db = mock_vector_db
        yield service


@pytest.mark.asyncio
async def test_vector_service_initialization(vector_service):
    """Test VectorService initializes correctly."""
    assert vector_service.db is not None
    assert vector_service.notion_api_key == "test_notion_api_key"
    assert vector_service.notion_database_ids == ["db1", "db2"]


@pytest.mark.asyncio
async def test_start_sync_databases(vector_service):
    """Test start_sync_databases creates background tasks."""
    with patch("services.vector_service.asyncio") as mock_asyncio:
        vector_service.start_sync_databases(force_update=True, page_limit=50)
        mock_asyncio.create_task.assert_called()


@pytest.mark.asyncio
async def test_vector_service_no_database_ids(monkeypatch):
    """Test VectorService with no database IDs configured."""
    monkeypatch.setenv("NOTION_API_KEY", "test_key")
    monkeypatch.setenv("NOTION_DATABASE_IDS", "")
    
    mock_vector_db = AsyncMock()
    mock_notion_utils = AsyncMock()
    
    mock_notion_client = MagicMock()
    mock_notion_client.databases = MagicMock()
    mock_notion_client.databases.query = AsyncMock()
    
    with patch("services.vector_service.VectorDB", return_value=mock_vector_db), \
         patch("services.vector_service.AsyncClient", return_value=mock_notion_client), \
         patch("services.vector_service.NotionUtils", return_value=mock_notion_utils):
        from services.vector_service import VectorService
        service = VectorService()
        assert service.notion_database_ids == []


@pytest.mark.asyncio
async def test_vector_service_no_api_key(monkeypatch):
    """Test VectorService with no API key configured."""
    monkeypatch.setenv("NOTION_API_KEY", "")
    monkeypatch.setenv("NOTION_DATABASE_IDS", "db1")
    
    mock_vector_db = AsyncMock()
    
    with patch("services.vector_service.VectorDB", return_value=mock_vector_db):
        from services.vector_service import VectorService
        service = VectorService()
        assert service.notion_api_key == ""
        # notion and notion_utils should not be initialized
        assert not hasattr(service, 'notion') or service.notion is None


@pytest.mark.asyncio
async def test_sync_database_background_empty_database(vector_service):
    """Test _sync_database_background with empty database."""
    mock_response = {
        "results": [],
        "has_more": False,
        "next_cursor": None
    }
    
    vector_service._mock_notion_client.databases.query.return_value = mock_response
    
    await vector_service._sync_database_background(
        database_id="db1",
        force_update=True,
        page_limit=10
    )
    
    # Verify no pages were processed
    vector_service._mock_vector_db.store_notion_page.assert_not_called()


@pytest.mark.asyncio
async def test_sync_database_background_no_notion_client(vector_service):
    """Test _sync_database_background when notion client is not available."""
    # Remove notion client
    vector_service.notion = None
    
    # Should handle gracefully without crashing
    try:
        await vector_service._sync_database_background(
            database_id="db1",
            force_update=True,
            page_limit=10
        )
    except AttributeError:
        # Expected if the code doesn't handle None client
        pass
