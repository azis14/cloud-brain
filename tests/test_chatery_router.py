import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


# --- Global Mocks and Patches ---
# We patch the service instances in the router module directly.
# The router creates service instances at module level, so we need to patch them there.

# Mock for RAGService
mock_rag_service_instance = AsyncMock()
mock_rag_service_instance.answer_question.return_value = {
    "answer": "This is a default test answer."
}
mock_rag_service_instance.identify_message.return_value = "QUERY"  # Default to QUERY

# Mock for ChateryService
mock_chatery_service_instance = AsyncMock()

# Patch the service classes before the router module is imported
patch('services.rag_service.RAGService', return_value=mock_rag_service_instance).start()
patch('services.chatery_service.ChateryService', return_value=mock_chatery_service_instance).start()


# --- Pytest Fixtures ---

@pytest.fixture(scope="module")
def test_client():
    """
    Creates a TestClient for the FastAPI app.
    This fixture has 'module' scope, so the app and environment variables
    are set up only once per test file run, improving performance.
    """
    # Patch the module-level constant in the security module directly.
    # This is crucial because security.py reads the environment variable at import time.
    # We also patch os.environ for completeness.
    with patch('security.API_SECRET_KEY', 'test-secret-key', create=True), \
         patch.dict(os.environ, {
            "API_SECRET_KEY": "test-secret-key",
            "WHITELISTED_NUMBERS": "1234567890,9876543210",  # Default whitelist for tests
            "CHATERY_API_URL": "https://test.chatery.api",
            "CHATERY_API_KEY": "test-chatery-key",
            "CHATERY_PHONE_NUMBER_ID": "test-phone-id",
            "CHATERY_WEBHOOK_SECRET": "test-webhook-secret"
        }):
        # Import the app inside the fixture to ensure patches are active
        from main import app
        
        # Now patch the router module's service instances with our mocks
        import routers.chatery_router
        routers.chatery_router.rag_service = mock_rag_service_instance
        routers.chatery_router.chatery_service = mock_chatery_service_instance
        routers.chatery_router.vectorService = MagicMock()
        
        client = TestClient(app)
        yield client


@pytest.fixture(autouse=True)
def reset_mocks():
    """
    This fixture automatically runs before each test.
    It resets the call history of the global mocks, ensuring test isolation.
    """
    mock_rag_service_instance.reset_mock()
    mock_chatery_service_instance.reset_mock()
    # Reset default return values
    mock_rag_service_instance.identify_message.return_value = "QUERY"
    mock_rag_service_instance.answer_question.return_value = {"answer": "This is a default test answer."}


# --- Test Cases ---

@pytest.mark.asyncio
async def test_verify_webhook_success(test_client):
    """
    Test successful webhook verification with correct parameters.
    """
    # Arrange
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "test-webhook-secret",
        "hub.challenge": "12345"
    }

    # Act
    response = test_client.get("/chatery/webhook", params=params)

    # Assert
    assert response.status_code == 200
    assert response.text == "12345"


@pytest.mark.asyncio
async def test_verify_webhook_wrong_mode(test_client):
    """
    Test webhook verification fails with wrong mode.
    """
    # Arrange
    params = {
        "hub.mode": "unsubscribe",
        "hub.verify_token": "test-webhook-secret",
        "hub.challenge": "12345"
    }

    # Act
    response = test_client.get("/chatery/webhook", params=params)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Verification failed"


@pytest.mark.asyncio
async def test_verify_webhook_wrong_token(test_client):
    """
    Test webhook verification fails with wrong verify token.
    """
    # Arrange
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong-token",
        "hub.challenge": "12345"
    }

    # Act
    response = test_client.get("/chatery/webhook", params=params)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Verification failed"


@pytest.mark.asyncio
async def test_verify_webhook_missing_params(test_client):
    """
    Test webhook verification fails with missing parameters.
    """
    # Arrange
    params = {
        "hub.mode": "subscribe"
        # Missing hub.verify_token and hub.challenge
    }

    # Act
    response = test_client.get("/chatery/webhook", params=params)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Verification failed"


@pytest.mark.asyncio
async def test_receive_whitelisted_message(test_client):
    """
    Test receiving a valid message from a whitelisted number.
    It should call the RAG service and then the Chatery reply service.
    """
    # Arrange: Define the payload for a whitelisted number (Chatery/Meta format)
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "text",
                        "text": {
                            "body": "Hello, this is a test."
                        }
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.answer_question.return_value = {"answer": "Test answer from RAG."}

    # Act: Send the request to the webhook
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert: Check the outcome
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_chatery_service_instance.send_whatsapp_reply.assert_called()


@pytest.mark.asyncio
async def test_receive_non_whitelisted_message(test_client):
    """
    Test receiving a message from a non-whitelisted number.
    It should not call any services.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1111111111",  # Not in the default whitelist
                        "type": "text",
                        "text": {
                            "body": "Unauthorized message."
                        }
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_chatery_service_instance.send_whatsapp_reply.assert_not_called()


@pytest.mark.asyncio
async def test_receive_message_invalid_api_key(test_client):
    """
    Test that a request with an invalid API key is rejected.
    """
    # Arrange
    payload = {"entry": []}
    headers = {"X-API-KEY": "wrong-secret-key"}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Could not validate credentials"
    mock_rag_service_instance.answer_question.assert_not_called()


@pytest.mark.asyncio
async def test_receive_message_no_api_key(test_client):
    """
    Test that a request with no API key is rejected.
    """
    # Arrange
    payload = {"entry": []}

    # Act
    response = test_client.post("/chatery/webhook", json=payload)

    # Assert
    assert response.status_code == 401
    mock_rag_service_instance.answer_question.assert_not_called()


@pytest.mark.asyncio
async def test_receive_empty_entry(test_client):
    """
    Test that empty entry payload is handled gracefully.
    """
    # Arrange
    payload = {"entry": []}
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_receive_non_text_message(test_client):
    """
    Test that non-text messages are ignored.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "image",  # Not a text message
                        "image": {"url": "https://example.com/image.jpg"}
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_chatery_service_instance.send_whatsapp_reply.assert_not_called()


@pytest.mark.asyncio
async def test_receive_status_update(test_client):
    """
    Test that status updates are handled gracefully.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "statuses": [{
                        "id": "message_id_123",
                        "status": "delivered"
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_rag_service_exception_handling(test_client):
    """
    Test that if the RAG service fails, the error is handled gracefully.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "text",
                        "text": {"body": "This will fail."}
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.answer_question.side_effect = Exception("RAG service exploded")

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_sync_command(test_client):
    """
    Test that SYNC command triggers database synchronization.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "text",
                        "text": {"body": "sync database"}
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.identify_message.return_value = "SYNC"

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_rag_service_instance.identify_message.assert_called_once()


@pytest.mark.asyncio
async def test_query_command(test_client):
    """
    Test that QUERY command triggers question answering.
    """
    # Arrange
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "1234567890",
                        "type": "text",
                        "text": {"body": "What is the weather?"}
                    }]
                }
            }]
        }]
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.identify_message.return_value = "QUERY"
    mock_rag_service_instance.answer_question.return_value = {"answer": "It's sunny today."}

    # Act
    response = test_client.post("/chatery/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_rag_service_instance.identify_message.assert_called_once()
    mock_rag_service_instance.answer_question.assert_called_once()
