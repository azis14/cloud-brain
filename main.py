from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from notion_client import Client
import logging
from routers import vector_router
from security import Secured

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cloud Brain API",
    description="FastAPI application to interact with Notion API and provide RAG capabilities",
    version="1.0.0"
)

# Include routers
app.include_router(vector_router.router)

# Add CORS middleware
cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [origin.strip() for origin in cors_allow_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Notion client
notion_api_key = os.getenv("NOTION_API_KEY")
if not notion_api_key:
    raise ValueError("NOTION_API_KEY environment variable is required")

notion = Client(auth=notion_api_key)

# Dependency to get Notion client
def get_notion_client():
    return notion

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Cloud Brain API is running"}

@app.get("/health", dependencies=[Secured])
async def health_check():
    """Health check endpoint"""
    try:
        # Test Notion API connection
        notion.users.me()
        return {"status": "healthy", "notion_api": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)