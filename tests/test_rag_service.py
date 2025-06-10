import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import os
import sys

# Ensure the services directory is in sys.path for import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../services")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.rag_service import RAGService

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_api_key")
    monkeypatch.setenv("GOOGLE_MODEL", "test_google_model")
    monkeypatch.setenv("MAX_CONTEXT_CHUNKS", "2")
    monkeypatch.setenv("MIN_SIMILARITY_SCORE", "0.5")

@pytest.fixture
def rag_service(mock_env):
    with patch("services.rag_service.VectorDB") as MockVectorDB, \
         patch("services.rag_service.genai") as mock_genai:
        # Mock the vector DB
        mock_vector_db = MockVectorDB.return_value
        # Mock the generative model
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure.return_value = None
        return RAGService()

@pytest.mark.asyncio
async def test_answer_question_with_results(rag_service):
    # Patch vector_search to return mock results
    mock_results = [
        {
            "chunk_id": "1",
            "notion_page_id": "page1",
            "notion_database_id": "db1",
            "chunk_text": "This is a relevant chunk.",
            "similarity_score": 0.9,
            "page_url": "http://example.com/page1",
            "page_properties": {
                "Title": {"type": "title", "title": [{"plain_text": "Test Page"}]}
            },
            "chunk_index": 0,
            "last_edited_time": "2024-01-01T00:00:00Z"
        }
    ]
    rag_service.vector_db.vector_search = AsyncMock(return_value=mock_results)
    rag_service.model.generate_content_async = AsyncMock(return_value=MagicMock(text="The answer is 42."))

    result = await rag_service.answer_question("What is the answer?")
    assert result["answer"] == "The answer is 42."
    assert result["sources"][0]["chunk_id"] == "1"
    assert result["sources"][0]["page_title"] == "Test Page"
    assert result["context_used"] is True
    assert result["search_results_count"] == 1
    assert result["model_used"] == rag_service.model_name

@pytest.mark.asyncio
async def test_answer_question_no_results(rag_service):
    rag_service.vector_db.vector_search = AsyncMock(return_value=[])
    result = await rag_service.answer_question("Unknown question?")
    assert "couldn't find relevant information" in result["answer"]
    assert result["sources"] == []
    assert result["context_used"] is False
    assert result["search_results_count"] == 0

@pytest.mark.asyncio
async def test_generate_answer_error(rag_service):
    rag_service.vector_db.vector_search = AsyncMock(return_value=[
        {
            "chunk_id": "1",
            "notion_page_id": "page1",
            "notion_database_id": "db1",
            "chunk_text": "This is a relevant chunk.",
            "similarity_score": 0.9,
            "page_url": "http://example.com/page1",
            "page_properties": {},
            "chunk_index": 0,
            "last_edited_time": "2024-01-01T00:00:00Z"
        }
    ])
    rag_service.model.generate_content_async = AsyncMock(side_effect=Exception("Generation error"))
    result = await rag_service.answer_question("What is the answer?")
    assert "error while generating the answer" in result["answer"]

def test_extract_rich_text(rag_service):
    rich_text = [
        {"plain_text": "Hello, "},
        {"plain_text": "world!"}
    ]
    assert rag_service._extract_rich_text(rich_text) == "Hello, world!"
    assert rag_service._extract_rich_text([]) == ""

def test_build_prompt(rag_service):
    question = "What is AI?"
    context = "Context 1: AI is artificial intelligence."
    prompt = rag_service._build_prompt(question, context)
    assert "What is AI?" in prompt
    assert "AI is artificial intelligence." in prompt