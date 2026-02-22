"""
Chatery service for handling WhatsApp messages and interactions with Chatery Cloud API.
"""
import logging
import os
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ChateryService:
    """Service for handling WhatsApp messages and interactions with Chatery Cloud API."""

    def __init__(self):
        # Initialize Chatery API configuration
        self.api_url = os.getenv("CHATERY_API_URL", "")
        self.api_key = os.getenv("CHATERY_API_KEY", "")
        self.phone_number_id = os.getenv("CHATERY_PHONE_NUMBER_ID", "")
        self.webhook_secret = os.getenv("CHATERY_WEBHOOK_SECRET", "")

        if not self.api_url or not self.api_key or not self.phone_number_id:
            raise ValueError(
                "CHATERY_API_URL, CHATERY_API_KEY, and CHATERY_PHONE_NUMBER_ID environment variables are required"
            )

        logger.info(
            f"ChateryService initialized with API URL: {self.api_url} and phone number ID: {self.phone_number_id}"
        )

    def verify_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """
        Verify the webhook signature to ensure the request is from Chatery.

        Args:
            signature: The signature from the request header
            payload: The raw request body

        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("CHATERY_WEBHOOK_SECRET not configured, skipping signature verification")
            return True

        import hmac
        import hashlib

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        is_valid = hmac.compare_digest(signature, expected_signature)
        if not is_valid:
            logger.warning("Invalid webhook signature")
        return is_valid

    async def send_whatsapp_reply(self, recipient: str, message: str):
        """
        Sends a text message reply using the Chatery API.

        Args:
            recipient: The recipient's phone number (with country code, e.g., '1234567890')
            message: The message text to send
        """
        send_url = f"{self.api_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {
                "body": message
            }
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(send_url, json=payload, headers=headers)
            response.raise_for_status()
            logger.info(f"Successfully sent reply to {recipient}")
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error sending message to {recipient}: {e.response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"An error occurred while requesting {e.request.url!r}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while sending message to {recipient}: {str(e)}")
