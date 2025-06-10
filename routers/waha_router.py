"""
WAHA webhook router for handling incoming WhatsApp messages.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
from security import Secured
from services.rag_service import RAGService
from services.waha_service import WahaService
import logging, os

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/waha", tags=["WAHA"], dependencies=[Secured])

# Whitelist of allowed phone numbers (in international format without '+')
WHITELISTED_NUMBERS = set(os.getenv("WHITELISTED_NUMBERS", "").split(","))

WAHA_API_URL = os.getenv("WAHA_API_URL", "")
SESSION_NAME = os.getenv("WAHA_SESSION_NAME", "")

rag_service = RAGService()
waha_service = WahaService()

@router.post("/webhook")
async def receive_whatsapp_message(payload: dict):
    """
    Receives incoming WhatsApp messages from WAHA.
    """
    try:
        # Extract the relevant information from the WAHA payload
        # The exact structure may vary based on your WAHA version and configuration
        event_type = payload.get("event")
        if event_type == "message":
            message_payload = payload.get("payload", {})
            sender_number_full = message_payload.get("from")
            message_body = message_payload.get("body")

            if sender_number_full and message_body:
                # Extract the phone number without the '@c.us' suffix
                sender_number = sender_number_full.split('@')[0]

                # Check if the sender is in the whitelist
                if sender_number in WHITELISTED_NUMBERS:
                    # Process the message
                    answer = await rag_service.answer_question(message_body)
                    response_text = answer.get("answer", "I couldn't find relevant information to answer your question.")
                    await waha_service.send_whatsapp_reply(sender_number_full, response_text)
                else:
                    logger.warning(f"Unauthorized access attempt from {sender_number_full}")

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

    return {"status": "ok"}