import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from vector_db import VectorDB

@pytest.fixture
def vector_db(monkeypatch):
    # Patch MongoDB client and SentenceTransformer
    monkeypatch.setenv("MONGODB_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGODB_DATABASE", "test_db")
    monkeypatch.setenv("MONGODB_COLLECTION", "test_collection")
    monkeypatch.setenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    monkeypatch.setenv("MAX_CHUNK_TOKENS", "10")
    monkeypatch.setenv("CHUNK_OVERLAP_TOKENS", "2")
    with patch("vector_db.AsyncIOMotorClient") as mock_motor, \
         patch("vector_db.SentenceTransformer") as mock_st, \
         patch("vector_db.tiktoken.get_encoding") as mock_encoding:
        # Mock embedding model
        mock_model = MagicMock()
        mock_model.get_sentence_embedding_dimension.return_value = 3
        # Return a mock with .tolist()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_embedding
        mock_st.return_value = mock_model
        # Mock tokenizer
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.side_effect = lambda text: list(range(len(text.split())))
        mock_tokenizer.decode.side_effect = lambda tokens: " ".join(str(t) for t in tokens)
        mock_encoding.return_value = mock_tokenizer
        # Mock MongoDB collection
        mock_collection = MagicMock()
        mock_db = MagicMock()
        mock_motor.return_value.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        db = VectorDB()
        db.collection = mock_collection
        db.embedding_model = mock_model
        db.tokenizer = mock_tokenizer
        return db

def test_chunk_text_short(vector_db):
    text = "short text"
    chunks = vector_db.chunk_text(text)
    assert chunks == ["short text"]

def test_chunk_text_long(vector_db):
    text = "a b c d e f g h i j k l"
    # max_chunk_tokens=10, overlap=2, so expect 2 chunks
    chunks = vector_db.chunk_text(text)
    assert len(chunks) == 2

def test_generate_embedding(vector_db):
    emb = vector_db.generate_embedding("hello world")
    assert emb == [0.1, 0.2, 0.3]

@pytest.mark.asyncio
async def test_store_notion_page(vector_db):
    page_data = {
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Test"}]},
            "Description": {"type": "rich_text", "rich_text": [{"plain_text": "Desc"}]}
        },
        "url": "http://notion.so/page",
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-01T00:00:00Z"
    }
    # Mock collection methods
    vector_db.collection.find_one = AsyncMock(return_value=None)
    vector_db.collection.delete_many = AsyncMock()
    vector_db.collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="abc123"))
    result = await vector_db.store_notion_page("pageid", page_data, "dbid")
    assert result["status"] == "success"
    assert result["chunks_stored"] > 0

def test_extract_text_from_page(vector_db):
    page_data = {
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Test"}]},
            "Description": {"type": "rich_text", "rich_text": [{"plain_text": "Desc"}]},
            "Select": {"type": "select", "select": {"name": "Option"}},
            "Multi": {"type": "multi_select", "multi_select": [{"name": "A"}, {"name": "B"}]}
        },
        "content": [{"text": "Block1"}, {"text": "Block2"}]
    }
    text = vector_db._extract_text_from_page(page_data)
    assert "Title: Test" in text
    assert "Description: Desc" in text
    assert "Select: Option" in text
    assert "Multi: A, B" in text
    assert "Block1" in text
    assert "Block2" in text

def test_extract_rich_text(vector_db):
    arr = [{"plain_text": "A"}, {"plain_text": "B"}]
    assert vector_db._extract_rich_text(arr) == "AB"
    assert vector_db._extract_rich_text([]) == ""

@pytest.mark.asyncio
async def test_vector_search(vector_db):
    # Return a non-empty list with expected structure
    mock_result = [{
        "_id": "id1",
        "notion_page_id": "pid",
        "notion_database_id": "dbid",
        "chunk_text": "chunk",
        "similarity_score": 0.9,
        "page_url": "url",
        "page_properties": {},
        "chunk_index": 0,
        "last_edited_time": "2024-01-01"
    }]
    mock_cursor = AsyncMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_result)
    vector_db.collection.aggregate = MagicMock(return_value=mock_cursor)
    result = await vector_db.vector_search("query")
    assert isinstance(result, list)
    assert result[0]["chunk_id"] == "id1"

@pytest.mark.asyncio
async def test_fallback_text_search(vector_db):
    vector_db.collection.find = MagicMock(return_value=MagicMock(
        sort=MagicMock(return_value=MagicMock(
            limit=MagicMock(return_value=AsyncMock(to_list=AsyncMock(return_value=[
                {
                    "_id": "id2",
                    "notion_page_id": "pid2",
                    "notion_database_id": "dbid2",
                    "chunk_text": "chunk2",
                    "score": 0.8,
                    "page_url": "url2",
                    "page_properties": {},
                    "chunk_index": 1,
                    "last_edited_time": "2024-01-02"
                }
            ])))
        ))
    ))
    result = await vector_db._fallback_text_search("query", 1)
    assert isinstance(result, list)
    assert result[0]["chunk_id"] == "id2"

@pytest.mark.asyncio
async def test_get_stats(vector_db):
    vector_db.collection.count_documents = AsyncMock(return_value=5)
    vector_db.collection.distinct = AsyncMock(side_effect=[["p1", "p2"], ["d1"]])
    vector_db.db.command = AsyncMock(return_value={"storageSize": 12345})
    stats = await vector_db.get_stats()
    assert stats["total_chunks"] == 5
    assert stats["unique_pages"] == 2
    assert stats["unique_databases"] == 1
    assert stats["storage_size_bytes"] == 12345

@pytest.mark.asyncio
async def test_delete_page(vector_db):
    vector_db.collection.delete_many = AsyncMock(return_value=MagicMock(deleted_count=3))
    result = await vector_db.delete_page("pid")
    assert result["status"] == "success"
    assert result["deleted_chunks"] == 3