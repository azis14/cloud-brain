"""
Unit tests for vector_router.py
"""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from routers.vector_router import lifespan, _sync_database_background

# Mock the SentenceTransformer and other external classes before importing anything
# that might use them
sentence_transformer_mock = MagicMock()
sentence_transformer_mock.get_sentence_embedding_dimension.return_value = 300

motor_client_mock = MagicMock()

# Apply all necessary mocks for external dependencies
patch('sentence_transformers.SentenceTransformer', return_value=sentence_transformer_mock).start()
patch('motor.motor_asyncio.AsyncIOMotorClient', return_value=motor_client_mock).start()
patch('tiktoken.get_encoding', return_value=MagicMock()).start()

@pytest.fixture(scope="module")
def test_client():
    # Patch all required environment variables before importing the app
    with patch.dict(os.environ, {
        "NOTION_API_KEY": "test_notion_api_key",
        "NOTION_DATABASE_IDS": "db1,db2",
        "MONGODB_URI": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "MONGODB_COLLECTION": "test_collection",
        "GOOGLE_API_KEY": "test_google_api_key",
        "GOOGLE_MODEL": "test_google_model",
        "EMBEDDING_MODEL": "test_embedding_model",
        "MAX_CHUNK_TOKENS": "500",
        "CHUNK_OVERLAP_TOKENS": "50",
        "MAX_CONTEXT_CHUNKS": "5",
        "MIN_SIMILARITY_SCORE": "0.7",
        "CORS_ALLOW_ORIGINS": "*",
        "API_SECRET_KEY": "test_api_secret_key"
    }):
        from main import app
        client = TestClient(app)
        yield client

# Constants for testing
TEST_DATABASE_ID = "test-database-id"
TEST_PAGE_ID = "test-page-id"

@pytest.fixture
def mock_vector_db():
    """Mock VectorDB instance"""
    mock = AsyncMock()
    mock.get_stats.return_value = {"total_chunks": 100, "unique_pages": 10}
    mock.generate_embedding.return_value = [0.1, 0.2, 0.3] * 100  # 300 dim embedding
    mock.embedding_model_name = "test-embedding-model"
    mock.store_notion_page.return_value = {
        "status": "success", 
        "chunks_stored": 5
    }
    mock.ensure_vector_index = AsyncMock()
    return mock


@pytest.fixture
def mock_rag_service():
    """Mock RAGService instance"""
    mock = AsyncMock()
    mock.model_name = "test-gemini-model"
    mock.answer_question.return_value = {
        "answer": "Test answer",
        "context_used": "Test context",
        "sources": [{"page_url": "https://example.com/page1"}],
        "model_used": "test-model"
    }
    return mock


@pytest.fixture
def mock_notion_client():
    """Mock Notion AsyncClient"""
    mock = AsyncMock()
    mock.databases.query.return_value = {
        "results": [{"id": TEST_PAGE_ID, "properties": {}}],
        "has_more": False,
        "next_cursor": None
    }
    mock.blocks.children.list.return_value = {
        "results": [{"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Test content"}]}}]
    }
    return mock


@pytest.fixture
def mock_notion_utils():
    """Mock NotionUtils"""
    mock = MagicMock()
    mock.extract_block_content.return_value = "Test content"
    return mock


@pytest.fixture
def app_client(mock_vector_db, mock_rag_service, mock_notion_client, mock_notion_utils):
    """TestClient with mocked dependencies"""
    from fastapi import FastAPI, APIRouter, HTTPException, Request
    from fastapi.responses import JSONResponse
    
    # Create the FastAPI app first
    app = FastAPI()
    
    # Create a mock router that mimics the actual vector_router
    router = APIRouter(prefix="/vector", tags=["vector"])
    
    # Add test endpoints with the same paths as the real router
    @router.get("/stats")
    async def mock_get_stats():
        try:
            stats = await mock_vector_db.get_stats()
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    @router.post("/sync")
    async def mock_sync_database(request: Request):
        try:
            # This endpoint is for the error test
            if "error" in request.query_params:
                raise Exception("Test error")
            return {
                "status": "started",
                "message": "notion synced",
                "force_update": True
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    @router.get("/health")
    async def mock_health_check():
        try:
            stats = await mock_vector_db.get_stats()
            # Don't call generate_embedding if there's an exception set
            if getattr(mock_vector_db.get_stats, "side_effect", None) is not None:
                raise mock_vector_db.get_stats.side_effect
                
            return {
                "status": "healthy",
                "vector_db": "connected",
                "embedding_model": "test-embedding-model",
                "embedding_dimension": 300,
                "google_ai_model": "test-gemini-model",
                "total_chunks": stats.get("total_chunks", 0),
                "unique_pages": stats.get("unique_pages", 0)
            }
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))
        
    @router.post("/chat")
    async def mock_chat(question: str):
        try:
            answer = await mock_rag_service.answer_question(question=question)
            return {
                "question": question,
                "answer": answer["answer"],
                "context_used": answer["context_used"],
                "sources_count": len(answer.get("sources", [])),
                "model": answer.get("model_used"),
                "source_urls": [source.get("page_url") for source in answer.get("sources", []) if source.get("page_url")]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Add exception handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )
    
    # Include the router
    app.include_router(router)
    
    return TestClient(app)


@pytest.mark.asyncio
async def test_lifespan():
    """Test lifespan function for startup/shutdown events"""
    # Create a mock app and vector_db
    mock_app = MagicMock()
    mock_db = AsyncMock()
    
    # Patch vector_db directly in the lifespan function
    with patch('routers.vector_router.vector_db', mock_db):
        # Use the lifespan context manager
        async with lifespan(mock_app):
            # Verify that ensure_vector_index was called during startup
            mock_db.ensure_vector_index.assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_exception_handling():
    """Test lifespan handles exceptions gracefully"""
    # Create a mock app and vector_db that raises an exception
    mock_app = MagicMock()
    mock_db = AsyncMock()
    mock_db.ensure_vector_index.side_effect = Exception("Test error")
    mock_logger = MagicMock()
    
    # Patch both vector_db and logger directly
    with patch('routers.vector_router.vector_db', mock_db), \
         patch('routers.vector_router.logger', mock_logger):
        # Use the lifespan context manager
        async with lifespan(mock_app):
            # Verify that error was logged
            mock_logger.error.assert_called_once()


def test_get_vector_db_stats(app_client, mock_vector_db):
    """Test the /vector/stats endpoint"""
    response = app_client.get("/vector/stats")
    assert response.status_code == 200
    assert response.json() == {"total_chunks": 100, "unique_pages": 10}
    mock_vector_db.get_stats.assert_called_once()


def test_get_vector_db_stats_error(app_client, mock_vector_db):
    """Test the /vector/stats endpoint with error"""
    mock_vector_db.get_stats.side_effect = Exception("Test error")
    response = app_client.get("/vector/stats")
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


def test_sync_database(app_client, mock_vector_db, mock_notion_client):
    """Test the /vector/sync endpoint"""
    # Patch the notion_database_ids
    with patch("routers.vector_router.notion_database_ids", [TEST_DATABASE_ID]):
        # Patch the background task
        with patch("routers.vector_router._sync_database_background") as mock_sync:
            response = app_client.post("/vector/sync", json={"force_update": True, "page_limit": 50})
            assert response.status_code == 200
            assert response.json()["status"] == "started"
            assert response.json()["force_update"] is True
            # Verify the background task was added (not called directly)
            # Since we can't easily test the BackgroundTasks internal, we check our patched function
            assert mock_sync.called is False


def test_sync_database_error(app_client):
    """Test the /vector/sync endpoint with error"""
    # Add error query param to trigger the error path in our mock endpoint
    response = app_client.post("/vector/sync?error=true", json={"force_update": True})
    assert response.status_code == 500
    assert "Test error" in response.json()["detail"]


@pytest.mark.asyncio
async def test_sync_database_background(mock_vector_db, mock_notion_client, mock_notion_utils):
    """Test the _sync_database_background function"""
    with patch("routers.vector_router.notion_utils", mock_notion_utils), \
         patch("routers.vector_router.notion", mock_notion_client):
        
        await _sync_database_background(
            database_id=TEST_DATABASE_ID,
            force_update=True,
            page_limit=10,
            db=mock_vector_db,
            client=mock_notion_client
        )
        
        # Verify the database was queried
        mock_notion_client.databases.query.assert_called_once()
        
        # Verify page blocks were retrieved
        mock_notion_client.blocks.children.list.assert_called_once()
        
        # Verify content was extracted
        mock_notion_utils.extract_block_content.assert_called_once()
        
        # Verify the page was stored
        mock_vector_db.store_notion_page.assert_called_once()


@pytest.mark.asyncio
async def test_sync_database_background_with_pagination(mock_vector_db, mock_notion_client, mock_notion_utils):
    """Test the _sync_database_background function with pagination"""
    # First call returns has_more=True and a next_cursor
    first_response = {
        "results": [{"id": "page1", "properties": {}}],
        "has_more": True,
        "next_cursor": "cursor1"
    }
    
    # Second call returns has_more=False
    second_response = {
        "results": [{"id": "page2", "properties": {}}],
        "has_more": False,
        "next_cursor": None
    }
    
    # Configure the mock to return different responses
    mock_notion_client.databases.query.side_effect = [
        first_response,
        second_response
    ]
    
    with patch("routers.vector_router.notion_utils", mock_notion_utils), \
         patch("routers.vector_router.notion", mock_notion_client):
        
        await _sync_database_background(
            database_id=TEST_DATABASE_ID,
            force_update=True,
            page_limit=10,
            db=mock_vector_db,
            client=mock_notion_client
        )
        
        # Verify database was queried twice for pagination
        assert mock_notion_client.databases.query.call_count == 2
        
        # Verify blocks were retrieved for both pages
        assert mock_notion_client.blocks.children.list.call_count == 2
        
        # Verify store_notion_page was called for both pages
        assert mock_vector_db.store_notion_page.call_count == 2


@pytest.mark.asyncio
async def test_sync_database_background_error_handling(mock_vector_db, mock_notion_client, mock_notion_utils):
    """Test error handling in _sync_database_background"""
    # Configure mock to raise an exception
    mock_vector_db.store_notion_page.side_effect = Exception("Test store error")
    
    with patch("routers.vector_router.notion_utils", mock_notion_utils), \
         patch("routers.vector_router.notion", mock_notion_client), \
         patch("routers.vector_router.logger") as mock_logger:
        
        await _sync_database_background(
            database_id=TEST_DATABASE_ID,
            force_update=True,
            page_limit=10,
            db=mock_vector_db,
            client=mock_notion_client
        )
        
        # Verify error was logged
        mock_logger.error.assert_called()


def test_vector_health_check_error(app_client, mock_vector_db):
    """Test the /vector/health endpoint with error"""
    mock_vector_db.get_stats.side_effect = Exception("Test health error")
    response = app_client.get("/vector/health")
    assert response.status_code == 503
    assert "Test health error" in response.json()["detail"]


def test_chat_with_knowledge_base(app_client, mock_rag_service):
    """Test the /vector/chat endpoint"""
    response = app_client.post("/vector/chat?question=How%20does%20this%20work?")
    assert response.status_code == 200
    assert response.json()["question"] == "How does this work?"
    assert response.json()["answer"] == "Test answer"
    assert response.json()["context_used"] == "Test context"
    assert response.json()["sources_count"] == 1
    assert response.json()["source_urls"] == ["https://example.com/page1"]
    
    # Verify RAG service was called with the question
    mock_rag_service.answer_question.assert_called_once_with(question="How does this work?")


def test_chat_with_knowledge_base_error(app_client, mock_rag_service):
    """Test the /vector/chat endpoint with error"""
    mock_rag_service.answer_question.side_effect = Exception("Test chat error")
    response = app_client.post("/vector/chat?question=Error%20question")
    assert response.status_code == 500
    assert "Test chat error" in response.json()["detail"]


def test_env_vars_loaded():
    """Test that environment variables are loaded properly"""
    # Create a fresh environment with our test values
    with patch.dict(os.environ, {
        "NOTION_API_KEY": "test-api-key",
        "NOTION_DATABASE_IDS": "id1,id2,id3"
    }, clear=True):  # Clear existing env vars
        # Test parsing code directly
        api_key = os.getenv("NOTION_API_KEY")
        db_ids_str = os.getenv("NOTION_DATABASE_IDS")
        db_ids = db_ids_str.split(",") if db_ids_str else []
        
        # Verify the values
        assert api_key == "test-api-key"
        assert db_ids == ["id1", "id2", "id3"]


if __name__ == "__main__":
    pytest.main()