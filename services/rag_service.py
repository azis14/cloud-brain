"""
RAG (Retrieval-Augmented Generation) service using Google AI Studio
"""
import os
import logging
from typing import List, Dict, Any
import google.generativeai as genai
from dotenv import load_dotenv
from vector_db import VectorDB
from utils.prompt_utils import PromptUtils

load_dotenv()
logger = logging.getLogger(__name__)

class RAGService:
    """RAG service for question answering using vector search and Google AI"""
    
    def __init__(self):
        # Initialize Google AI
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY environment variable is required")
        
        genai.configure(api_key=self.google_api_key)
        
        # Initialize model
        self.model_name = os.getenv("GOOGLE_MODEL", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(self.model_name)
        
        # Initialize vector database
        self.vector_db = VectorDB()
        
        # Configuration
        self.max_context_chunks = int(os.getenv("MAX_CONTEXT_CHUNKS", "5"))
        self.min_similarity_score = float(os.getenv("MIN_SIMILARITY_SCORE", "0.7"))
        
        logger.info(f"RAG service initialized with model: {self.model_name}")

    async def identify_message(
        self,
        message: str,
    ) -> str:
        """Identify the type of message"""
        prompt = PromptUtils.build_identify_prompt(message)

        response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    top_p=0.8,
                    top_k=40
                )
            )
            
        return response.text.strip()
    
    async def answer_question(
        self,
        question: str,
    ) -> Dict[str, Any]:
        """Answer a question using RAG"""
        try:
            # Retrieve relevant context from vector database
            search_results = await self.vector_db.vector_search(
                query=question,
                limit=self.max_context_chunks,
                min_score=self.min_similarity_score
            )
            
            if not search_results:
                return {
                    "answer": "I couldn't find relevant information in your knowledge base to answer this question.",
                    "sources": [],
                    "context_used": False,
                    "search_results_count": 0
                }
            
            print(f"Found {len(search_results)} relevant chunks for the question.")
            print("Search results:", search_results)
            
            # Build context from search results
            context_parts = []
            sources = []
            
            for i, result in enumerate(search_results):
                context_parts.append(f"Context {i+1}:\n{result['chunk_text']}")
                
                source = {
                    "chunk_id": result["chunk_id"],
                    "notion_page_id": result["notion_page_id"],
                    "page_url": result.get("page_url"),
                    "similarity_score": result["similarity_score"],
                    "chunk_text": result["chunk_text"][:200] + "..." if len(result["chunk_text"]) > 200 else result["chunk_text"]
                }
                
                page_props = result.get("page_properties", {})
                for prop_name, prop_data in page_props.items():
                    if prop_data.get("type") == "title":
                        title_text = self._extract_rich_text(prop_data.get("title", []))
                        if title_text:
                            source["page_title"] = title_text
                            break
                
                sources.append(source)
            
            context = "\n\n".join(context_parts)
            
            # Generate answer using Google AI
            answer = await self._generate_answer(question, context)
            
            return {
                "answer": answer,
                "sources": sources,
                "context_used": True,
                "search_results_count": len(search_results),
                "model_used": self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error answering question: {str(e)}")
            raise
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Generate answer using Google AI with context"""
        try:
            prompt = PromptUtils.build_question_prompt(question, context)
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=1000,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return f"I encountered an error while generating the answer: {str(e)}"
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array"""
        if not rich_text_array:
            return ""
        
        return "".join([
            text_obj.get("plain_text", "") 
            for text_obj in rich_text_array
        ])
    
    async def close(self):
        """Close connections"""
        await self.vector_db.close()