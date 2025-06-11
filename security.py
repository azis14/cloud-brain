from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_SECRET_KEY = os.getenv("API_SECRET_KEY")
if not API_SECRET_KEY:
    raise ValueError("API_SECRET_KEY environment variable is not set")

# Define the API Key Header
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    """
    Dependency function to validate the API key from the X-API-KEY header.
    
    FastAPI will automatically handle calling this for every protected endpoint.
    Swagger UI will also automatically recognize this and provide an
    "Authorize" button to enter the API key.
    """
    if api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials"
        )
    return api_key

Secured = Depends(get_api_key)