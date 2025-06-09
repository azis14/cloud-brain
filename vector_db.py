"""
Vector database utilities for storing and retrieving embeddings in MongoDB Atlas
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import numpy as np
from motor.motor_asyncio import AsyncIOMotorClient
from sentence_transformers import SentenceTransformer
import tiktoken
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class VectorDB:
    """Vector database manager for MongoDB Atlas with vector search capabilities"""
    
    def __init__(self):
        self.mongodb_uri = os.getenv("MONGODB_URI")
        if not self.mongodb_uri:
            raise ValueError("MONGODB_URI environment variable is required")
        
        self.database_name = os.getenv("MONGODB_DATABASE", "second_brain")
        self.collection_name = os.getenv("MONGODB_COLLECTION", "knowledge_base")
        
        # Initialize MongoDB client
        self.client = AsyncIOMotorClient(self.mongodb_uri)
        self.db = self.client[self.database_name]
        self.collection = self.db[self.collection_name]
        
        # Initialize embedding model
        self.embedding_model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.embedding_model = SentenceTransformer(self.embedding_model_name)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize tokenizer for text chunking
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.max_chunk_tokens = int(os.getenv("MAX_CHUNK_TOKENS", "500"))
        self.chunk_overlap_tokens = int(os.getenv("CHUNK_OVERLAP_TOKENS", "50"))
        
        logger.info(f"VectorDB initialized with model: {self.embedding_model_name}")
        logger.info(f"Embedding dimension: {self.embedding_dimension}")
    
    async def ensure_vector_index(self):
        """Ensure vector search index exists in MongoDB Atlas"""
        try:
            # Check if index already exists
            indexes = await self.collection.list_indexes().to_list(length=None)
            vector_index_exists = any(
                index.get("name") == "vector_index" for index in indexes
            )
            
            if not vector_index_exists:
                logger.info("Creating vector search index...")
                # Note: Vector search index creation in MongoDB Atlas is typically done via Atlas UI or Atlas CLI
                # This is a placeholder for the index definition
                index_definition = {
                    "name": "vector_index",
                    "definition": {
                        "fields": [
                            {
                                "type": "vector",
                                "path": "embedding",
                                "numDimensions": self.embedding_dimension,
                                "similarity": "cosine"
                            }
                        ]
                    }
                }
                logger.warning("Vector index should be created manually in MongoDB Atlas")
                logger.info(f"Index definition: {index_definition}")
            else:
                logger.info("Vector search index already exists")
                
        except Exception as e:
            logger.error(f"Error checking/creating vector index: {str(e)}")
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        if not text.strip():
            return []
        
        # Tokenize the text
        tokens = self.tokenizer.encode(text)
        
        if len(tokens) <= self.max_chunk_tokens:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Calculate end position
            end = min(start + self.max_chunk_tokens, len(tokens))
            
            # Extract chunk tokens
            chunk_tokens = tokens[start:end]
            
            # Decode back to text
            chunk_text = self.tokenizer.decode(chunk_tokens)
            chunks.append(chunk_text.strip())
            
            # Move start position with overlap
            if end >= len(tokens):
                break
            start = end - self.chunk_overlap_tokens
        
        return chunks
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    async def store_notion_page(
        self, 
        page_id: str, 
        page_data: Dict[str, Any],
        database_id: str,
        force_update: bool = False
    ) -> Dict[str, Any]:
        """Store a Notion page as vector embeddings"""
        try:
            # Check if page already exists and is up to date
            existing_doc = await self.collection.find_one({"notion_page_id": page_id})
            
            page_last_edited = page_data.get("last_edited_time")
            if existing_doc and not force_update:
                stored_last_edited = existing_doc.get("last_edited_time")
                if stored_last_edited == page_last_edited:
                    logger.info(f"Page {page_id} is up to date, skipping")
                    return {"status": "skipped", "reason": "up_to_date"}
            
            # Extract text content from page properties
            text_content = self._extract_text_from_page(page_data)
            
            if not text_content.strip():
                logger.warning(f"No text content found in page {page_id}")
                return {"status": "skipped", "reason": "no_content"}
            
            # Chunk the text
            chunks = self.chunk_text(text_content)
            logger.info(f"Created {len(chunks)} chunks for page {page_id}")
            
            # Delete existing chunks for this page
            await self.collection.delete_many({"notion_page_id": page_id})
            
            # Store each chunk with its embedding
            stored_chunks = []
            for i, chunk in enumerate(chunks):
                embedding = self.generate_embedding(chunk)
                
                chunk_doc = {
                    "notion_page_id": page_id,
                    "notion_database_id": database_id,
                    "chunk_index": i,
                    "chunk_text": chunk,
                    "embedding": embedding,
                    "page_properties": page_data.get("properties", {}),
                    "page_url": page_data.get("url"),
                    "created_time": page_data.get("created_time"),
                    "last_edited_time": page_data.get("last_edited_time"),
                    "stored_at": datetime.utcnow().isoformat(),
                    "embedding_model": self.embedding_model_name,
                    "chunk_tokens": len(self.tokenizer.encode(chunk))
                }
                
                result = await self.collection.insert_one(chunk_doc)
                stored_chunks.append({
                    "chunk_id": str(result.inserted_id),
                    "chunk_index": i,
                    "chunk_tokens": chunk_doc["chunk_tokens"]
                })
            
            return {
                "status": "success",
                "page_id": page_id,
                "chunks_stored": len(stored_chunks),
                "chunks": stored_chunks,
                "total_tokens": sum(chunk["chunk_tokens"] for chunk in stored_chunks)
            }
            
        except Exception as e:
            logger.error(f"Error storing page {page_id}: {str(e)}")
            raise
    
    def _extract_text_from_page(self, page_data: Dict[str, Any]) -> str:
        """Extract text content from Notion page data"""
        text_parts = []
        
        # Extract from properties
        properties = page_data.get("properties", {})
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
            if prop_type == "title":
                title_text = self._extract_rich_text(prop_data.get("title", []))
                if title_text:
                    text_parts.append(f"Title: {title_text}")
            
            elif prop_type == "rich_text":
                rich_text = self._extract_rich_text(prop_data.get("rich_text", []))
                if rich_text:
                    text_parts.append(f"{prop_name}: {rich_text}")
            
            elif prop_type == "select":
                select_data = prop_data.get("select")
                if select_data and select_data.get("name"):
                    text_parts.append(f"{prop_name}: {select_data['name']}")
            
            elif prop_type == "multi_select":
                multi_select_data = prop_data.get("multi_select", [])
                if multi_select_data:
                    values = [item.get("name", "") for item in multi_select_data]
                    text_parts.append(f"{prop_name}: {', '.join(values)}")

        contents = page_data.get("content", [])
        for content in contents:
            text_parts.append(content.get("text", ""))
        
        return "\n".join(text_parts)
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array"""
        if not rich_text_array:
            return ""
        
        return "".join([
            text_obj.get("plain_text", "") 
            for text_obj in rich_text_array
        ])
    
    async def vector_search(
        self, 
        query: str, 
        limit: int = 30,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search"""
        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query)
            
            # Build aggregation pipeline
            pipeline = []
            
            # Vector search stage (MongoDB Atlas Vector Search)
            vector_search_stage = {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": limit * 10,
                    "limit": limit
                }
            }

            pipeline.append(vector_search_stage)
            
            # Add score to results
            pipeline.append({
                "$addFields": {
                    "similarity_score": {"$meta": "vectorSearchScore"}
                }
            })
            
            # Filter by minimum score
            pipeline.append({
                "$match": {
                    "similarity_score": {"$gte": min_score}
                }
            })
            
            # Execute search
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=limit)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_result = {
                    "chunk_id": str(result["_id"]),
                    "notion_page_id": result["notion_page_id"],
                    "notion_database_id": result["notion_database_id"],
                    "chunk_text": result["chunk_text"],
                    "similarity_score": result["similarity_score"],
                    "page_url": result.get("page_url"),
                    "page_properties": result.get("page_properties", {}),
                    "chunk_index": result.get("chunk_index", 0),
                    "last_edited_time": result.get("last_edited_time")
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in vector search: {str(e)}")
            # Fallback to text search if vector search fails
            return await self._fallback_text_search(query, limit)
    
    async def _fallback_text_search(
        self, 
        query: str, 
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Fallback text search when vector search is not available"""
        try:
            match_filter = {"$text": {"$search": query}}
            
            cursor = self.collection.find(
                match_filter,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            results = await cursor.to_list(length=limit)
            
            formatted_results = []
            for result in results:
                formatted_result = {
                    "chunk_id": str(result["_id"]),
                    "notion_page_id": result["notion_page_id"],
                    "notion_database_id": result["notion_database_id"],
                    "chunk_text": result["chunk_text"],
                    "similarity_score": result.get("score", 0.5),  # Text search score
                    "page_url": result.get("page_url"),
                    "page_properties": result.get("page_properties", {}),
                    "chunk_index": result.get("chunk_index", 0),
                    "last_edited_time": result.get("last_edited_time")
                }
                formatted_results.append(formatted_result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in fallback text search: {str(e)}")
            return []
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            total_chunks = await self.collection.count_documents({})
            unique_pages = len(await self.collection.distinct("notion_page_id"))
            unique_databases = len(await self.collection.distinct("notion_database_id"))
            
            # Get storage size (approximate)
            stats = await self.db.command("collStats", self.collection_name)
            storage_size = stats.get("storageSize", 0)
            
            return {
                "total_chunks": total_chunks,
                "unique_pages": unique_pages,
                "unique_databases": unique_databases,
                "storage_size_bytes": storage_size,
                "embedding_model": self.embedding_model_name,
                "embedding_dimension": self.embedding_dimension
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {}
    
    async def delete_page(self, page_id: str) -> Dict[str, Any]:
        """Delete all chunks for a specific page"""
        try:
            result = await self.collection.delete_many({"notion_page_id": page_id})
            return {
                "status": "success",
                "deleted_chunks": result.deleted_count
            }
        except Exception as e:
            logger.error(f"Error deleting page {page_id}: {str(e)}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()