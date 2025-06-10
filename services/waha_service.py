"""
WAHA service for handling WhatsApp messages and interactions with WAHA API.
"""
import logging, os, httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class WahaService:
    """Service for handling WhatsApp messages and interactions with WAHA API."""
    
    def __init__(self):
        # Initialize WAHA API configuration
        self.api_url = os.getenv("WAHA_API_URL", "")
        self.api_key = os.getenv("WAHA_API_KEY", "")
        self.session_name = os.getenv("WAHA_SESSION_NAME", "")
        
        if not self.api_url or not self.session_name or not self.api_key:
            raise ValueError("WAHA_API_URL, WAHA_API_KEY, and WAHA_SESSION_NAME environment variables are required")
        
        logger.info(f"WahaService initialized with API URL: {self.api_url} and session name: {self.session_name}")
    
    async def send_whatsapp_reply(self, recipient: str, message: str):
        """
        Sends a text message reply using the WAHA API.
        """
        send_url = f"{self.api_url}/sendText"
        payload = {
            "chatId": recipient,
            "text": message,
            "session": self.session_name,
        }
        headers = {
            "X-Api-Key": self.api_key,
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(send_url, json=payload, headers=headers)
                response.raise_for_status()
                logger.info(f"Successfully sent reply to {recipient}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Error sending message to {recipient}: {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting {e.request.url!r}.")