"""
    Vector Service for handling data vector
"""

import logging
import os

from fastapi import BackgroundTasks
from vector_db import VectorDB
from typing import Optional
from notion_client import AsyncClient
from utils.notion_utils import NotionUtils
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class VectorService:
    """Vector service for handling data vector operations."""
    
    def __init__(self):
        self.db = VectorDB()
        self.notion_api_key = os.getenv("NOTION_API_KEY")
        self.notion_database_ids = os.getenv("NOTION_DATABASE_IDS", "").split(",") if os.getenv("NOTION_DATABASE_IDS") else []
        self.background_tasks = BackgroundTasks()

        if self.notion_api_key:
            self.notion = AsyncClient(auth=self.notion_api_key)
            self.notion_utils = NotionUtils(self.notion)

        logger.info("Vector service initialized")

    def start_sync_databases(self, force_update: bool = True, page_limit: Optional[int] = 100):
        """Start syncing Notion databases in the background"""
        for database_id in self.notion_database_ids:
            self.background_tasks.add_task(
                self._sync_database_background,
                database_id,
                force_update,
                page_limit
            )

    
    async def _sync_database_background(
        self,
        database_id: str,
        force_update: bool,
        page_limit: Optional[int]
    ):
        """Background task to sync database"""
        try:
            logger.info(f"Starting background sync for database {database_id}")
            
            # Get all pages from the database
            all_pages = []
            has_more = True
            next_cursor = None
            pages_processed = 0
            
            while has_more and (page_limit is None or pages_processed < page_limit):
                query_params = {
                    "database_id": database_id,
                    "page_size": min(100, page_limit - pages_processed if page_limit else 100)
                }
                if next_cursor:
                    query_params["start_cursor"] = next_cursor
                
                response = await self.notion.databases.query(**query_params)
                pages = response.get("results", [])
                all_pages.extend(pages)
                
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                pages_processed += len(pages)
                
                if page_limit and pages_processed >= page_limit:
                    break

            
            logger.info(f"Found {len(all_pages)} pages to sync")
            
            # Sync each page
            sync_results = {
                "success": 0,
                "skipped": 0,
                "errors": 0,
                "total_chunks": 0
            }
            
            for page in all_pages:
                pageContent = []
                blocks_response = await self.notion.blocks.children.list(block_id=page["id"])
                for block in blocks_response.get("results", []):
                    pageContent.append(self.notion_utils.extract_block_content(block))
                page["content"] = pageContent
                try:
                    result = await self.db.store_notion_page(
                        page_id=page["id"],
                        page_data=page,
                        database_id=database_id,
                        force_update=force_update
                    )
                    
                    if result["status"] == "success":
                        sync_results["success"] += 1
                        sync_results["total_chunks"] += result["chunks_stored"]
                    elif result["status"] == "skipped":
                        sync_results["skipped"] += 1
                        
                except Exception as e:
                    logger.error(f"Error syncing page {page['id']}: {str(e)}")
                    sync_results["errors"] += 1
            
            logger.info(f"Database sync completed: {sync_results}")
            
        except Exception as e:
            logger.error(f"Error in background database sync: {str(e)}")