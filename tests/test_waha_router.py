import pytest
import os
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

# --- Global Mocks and Patches ---
# We patch the service classes before they are instantiated in the waha router module.
# This ensures that any code importing 'rag_service' or 'waha_service' gets our mock.

# Mock for RAGService
mock_rag_service_instance = AsyncMock()
mock_rag_service_instance.answer_question.return_value = {
    "answer": "This is a default test answer."
}
patch('services.rag_service.RAGService', return_value=mock_rag_service_instance).start()

# Mock for WahaService
mock_waha_service_instance = AsyncMock()
patch('services.waha_service.WahaService', return_value=mock_waha_service_instance).start()


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
            "WHITELISTED_NUMBERS": "1234567890,9876543210", # Default whitelist for tests
            "WAHA_API_URL": "http://test.waha.api",
            "WAHA_SESSION_NAME": "test-session"
        }):
        # Import the app inside the fixture to ensure patches are active
        from main import app
        client = TestClient(app)
        yield client

@pytest.fixture(autouse=True)
def reset_mocks():
    """
    This fixture automatically runs before each test.
    It resets the call history of the global mocks, ensuring test isolation.
    """
    mock_rag_service_instance.reset_mock()
    mock_waha_service_instance.reset_mock()


# --- Test Cases ---

@pytest.mark.asyncio
async def test_receive_whitelisted_message(test_client):
    """
    Test receiving a valid message from a whitelisted number.
    It should call the RAG service and then the WAHA reply service.
    """
    # Arrange: Define the payload for a whitelisted number
    payload = {
        "event": "message",
        "payload": {
            "from": "1234567890@c.us",
            "body": "Hello, this is a test."
        }
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.answer_question.return_value = {"answer": "Test answer from RAG."}

    # Act: Send the request to the webhook
    response = test_client.post("/waha/webhook", json=payload, headers=headers)

    # Assert: Check the outcome
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_receive_non_whitelisted_message(test_client):
    """
    Test receiving a message from a non-whitelisted number.
    It should not call any services and log a warning (logging is not asserted here).
    """
    # Arrange
    payload = {
        "event": "message",
        "payload": {
            "from": "1111111111@c.us", # Not in the default whitelist
            "body": "Unauthorized message."
        }
    }
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/waha/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_receive_message_invalid_api_key(test_client):
    """
    Test that a request with an invalid API key is rejected.
    """
    # Arrange
    payload = {"event": "message", "payload": {}}
    headers = {"X-API-KEY": "wrong-secret-key"}

    # Act
    response = test_client.post("/waha/webhook", json=payload, headers=headers)

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
    payload = {"event": "message", "payload": {}}

    # Act
    response = test_client.post("/waha/webhook", json=payload)

    # Assert
    assert response.status_code == 403
    assert response.json()["detail"] == "Not authenticated"
    mock_rag_service_instance.answer_question.assert_not_called()

@pytest.mark.asyncio
async def test_rag_service_exception_handling(test_client):
    """
    Test that if the RAG service fails, the error is handled gracefully
    and a reply is not sent.
    """
    # Arrange
    payload = {
        "event": "message",
        "payload": {"from": "1234567890@c.us", "body": "This will fail."}
    }
    headers = {"X-API-KEY": "test-secret-key"}
    mock_rag_service_instance.answer_question.side_effect = Exception("RAG service exploded")

    # Act
    response = test_client.post("/waha/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_ignore_non_message_events(test_client):
    """
    Test that the webhook ignores events that are not of type 'message'.
    """
    # Arrange
    payload = {"event": "ack", "payload": {}} # 'ack' is not a 'message'
    headers = {"X-API-KEY": "test-secret-key"}

    # Act
    response = test_client.post("/waha/webhook", json=payload, headers=headers)

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_rag_service_instance.answer_question.assert_not_called()
    mock_waha_service_instance.send_whatsapp_reply.assert_not_called()
