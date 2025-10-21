"""
Vector database and RAG endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import Optional
from pydantic import BaseModel
import logging
from vector_db import VectorDB
from services.rag_service import RAGService
from services.vector_service import VectorService
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from security import Secured

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize services
vector_db = VectorDB()
rag_service = RAGService()
vector_service = VectorService()

@asynccontextmanager
async def lifespan(app):
    """Handle startup and shutdown events"""
    # Startup: Initialize vector database
    try:
        await vector_db.ensure_vector_index()
        logger.info("Vector database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing vector database: {str(e)}")
    
    yield  # This is where FastAPI serves requests

router = APIRouter(prefix="/vector", tags=["vector"], lifespan=lifespan)

class SyncRequest(BaseModel):
    force_update: bool = True
    page_limit: Optional[int] = 100

def get_vector_db():
    return vector_db

def get_rag_service():
    return rag_service

def get_vector_service():
    return vector_service

@router.get("/stats", dependencies=[Secured])
async def get_vector_db_stats(db: VectorDB = Depends(get_vector_db)):
    """Get vector database statistics"""
    try:
        stats = await db.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync", dependencies=[Secured])
async def sync_database(
    request: SyncRequest,
    vector: VectorService = Depends(get_vector_service)
):
    """Sync entire Notion database to vector database"""
    try:
        # Start background sync task
        vector.start_sync_databases(
            force_update=request.force_update,
            page_limit=request.page_limit)
        
        return {
            "status": "started",
            "message": "notion synced",
            "force_update": request.force_update
        }
    except Exception as e:
        logger.error(f"Error starting database sync: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health", dependencies=[Secured])
async def vector_health_check(
    db: VectorDB = Depends(get_vector_db),
    rag: RAGService = Depends(get_rag_service)
):
    """Health check for vector database and RAG service"""
    try:
        # Test vector database connection
        stats = await db.get_stats()
        
        # Test embedding generation
        test_embedding = db.generate_embedding("test")
        
        return {
            "status": "healthy",
            "vector_db": "connected",
            "embedding_model": db.embedding_model_name,
            "embedding_dimension": len(test_embedding),
            "google_ai_model": rag.model_name,
            "total_chunks": stats.get("total_chunks", 0),
            "unique_pages": stats.get("unique_pages", 0)
        }
        
    except Exception as e:
        logger.error(f"Vector health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

# Chat-like interface
@router.post("/chat", dependencies=[Secured])
async def chat_with_knowledge_base(
    question: str = Query(..., description="Your question"),
    rag: RAGService = Depends(get_rag_service)
):
    """Simple chat interface for asking questions"""
    try:
        answer = await rag.answer_question(
            question=question
        )
        
        # Format for chat-like response
        response = {
            "question": question,
            "answer": answer["answer"],
            "context_used": answer["context_used"],
            "sources_count": len(answer.get("sources", [])),
            "model": answer.get("model_used")
        }
        
        # Add source URLs if available
        if answer.get("sources"):
            response["source_urls"] = [
                source.get("page_url") for source in answer["sources"] 
                if source.get("page_url")
            ]
        
        return response
        
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))