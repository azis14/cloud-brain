"""
Chatery webhook router for handling incoming WhatsApp messages.
"""
from fastapi import APIRouter, Request, HTTPException
from dotenv import load_dotenv
from security import Secured
from services.rag_service import RAGService
from services.chatery_service import ChateryService
from services.vector_service import VectorService
import logging
import os

load_dotenv()
logger = logging.getLogger(__name__)

# Router without global security dependency - security is applied per-endpoint
router = APIRouter(prefix="/chatery", tags=["Chatery"])

# Whitelist of allowed phone numbers (in international format without '+')
WHITELISTED_NUMBERS = set(os.getenv("WHITELISTED_NUMBERS", "").split(","))

# Chatery configuration
CHATERY_WEBHOOK_SECRET = os.getenv("CHATERY_WEBHOOK_SECRET", "")

rag_service = RAGService()
chatery_service = ChateryService()
vectorService = VectorService()


@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verifies the webhook endpoint with Chatery.
    Chatery sends a GET request with verification parameters.
    """
    try:
        # Parse query parameters
        query_params = request.query_params
        mode = query_params.get("hub.mode")
        verify_token = query_params.get("hub.verify_token")
        challenge = query_params.get("hub.challenge")

        # Check if all required parameters are present
        if mode and verify_token and challenge:
            # Verify the mode and token
            if mode == "subscribe" and verify_token == CHATERY_WEBHOOK_SECRET:
                logger.info("Webhook verification successful")
                return int(challenge)

        logger.warning("Webhook verification failed")
        raise HTTPException(status_code=403, detail="Verification failed")
    except Exception as e:
        logger.error(f"Error during webhook verification: {str(e)}")
        raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook", dependencies=[Secured])
async def receive_whatsapp_message(request: Request):
    """
    Receives incoming WhatsApp messages from Chatery.
    """
    try:
        # Get the raw body for signature verification
        body = await request.body()
        payload = await request.json()

        # Verify webhook signature if secret is configured
        if CHATERY_WEBHOOK_SECRET:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if signature:
                # Extract the signature value (remove 'sha256=' prefix if present)
                if signature.startswith("sha256="):
                    signature = signature[7:]
                if not chatery_service.verify_webhook_signature(signature, body):
                    logger.warning("Invalid webhook signature")
                    raise HTTPException(status_code=401, detail="Invalid signature")

        # Extract message data from Chatery payload
        # Chatery/Meta format: entry[0].changes[0].value.messages[0]
        entry = payload.get("entry", [])
        if not entry:
            return {"status": "ok"}

        change = entry[0].get("changes", [{}])[0]
        value = change.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ok"}

        message = messages[0]
        message_type = message.get("type")

        # Only process text messages
        if message_type == "text":
            sender_number = message.get("from")
            message_body = message.get("text", {}).get("body")

            if sender_number and message_body:
                # Check if the sender is in the whitelist
                if sender_number in WHITELISTED_NUMBERS:
                    # Process the message
                    type_identification = await rag_service.identify_message(message_body)

                    logger.info(f"Message from {sender_number}: {message_body}")
                    logger.info(f"Identified message type: {type_identification}")

                    if type_identification == "SYNC":
                        await chatery_service.send_whatsapp_reply(
                            sender_number,
                            "Sync command received. Starting synchronization..."
                        )
                        vectorService.start_sync_databases(force_update=True, page_limit=100)
                        await chatery_service.send_whatsapp_reply(
                            sender_number,
                            "Synchronization started in the background."
                        )
                    elif type_identification == "QUERY":
                        answer = await rag_service.answer_question(message_body)
                        response_text = answer.get(
                            "answer",
                            "I couldn't find relevant information to answer your question."
                        )
                        await chatery_service.send_whatsapp_reply(sender_number, response_text)
                    else:
                        await chatery_service.send_whatsapp_reply(
                            sender_number,
                            "I'm sorry, I couldn't identify the intention of your message."
                        )
                else:
                    logger.warning(f"Unauthorized access attempt from {sender_number}")

        # Handle status updates (message delivered, read, etc.)
        statuses = value.get("statuses", [])
        if statuses:
            for status in statuses:
                status_type = status.get("status")
                message_id = status.get("id")
                logger.info(f"Message status update: {message_id} - {status_type}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")

    return {"status": "ok"}
