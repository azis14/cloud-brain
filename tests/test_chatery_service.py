import pytest
from unittest.mock import MagicMock
from services.chatery_service import ChateryService
import requests
import os
import asyncio


@pytest.fixture
def set_env_vars(monkeypatch):
    """Fixture to set environment variables for tests."""
    monkeypatch.setenv("CHATERY_API_URL", "https://fake.chatery.api")
    monkeypatch.setenv("CHATERY_API_KEY", "fake_chatery_key")
    monkeypatch.setenv("CHATERY_PHONE_NUMBER_ID", "fake_phone_id")
    monkeypatch.setenv("CHATERY_WEBHOOK_SECRET", "fake_webhook_secret")


@pytest.mark.asyncio
async def test_send_whatsapp_reply_success(mocker, set_env_vars):
    """Test successful message sending via Chatery API."""
    # Arrange
    service = ChateryService()
    mock_post = mocker.patch("services.chatery_service.requests.post")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Act
    await service.send_whatsapp_reply("1234567890", "Hello, world!")

    # Assert
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert call_args[0][0] == "https://fake.chatery.api/messages"
    assert call_args[1]["json"]["to"] == "1234567890"
    assert call_args[1]["json"]["text"]["body"] == "Hello, world!"
    assert call_args[1]["headers"]["Authorization"] == "Bearer fake_chatery_key"


@pytest.mark.asyncio
async def test_send_whatsapp_reply_http_error(mocker, set_env_vars, caplog):
    """Test handling HTTP errors during message sending."""
    # Arrange
    service = ChateryService()
    mock_post = mocker.patch("services.chatery_service.requests.post")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=MagicMock(text="HTTP Error")
    )
    mock_post.return_value = mock_response

    # Act
    with caplog.at_level("ERROR"):
        await service.send_whatsapp_reply("1234567890", "Hello, world!")

    # Assert
    assert "Error sending message" in caplog.text


@pytest.mark.asyncio
async def test_send_whatsapp_reply_request_error(mocker, set_env_vars, caplog):
    """Test handling RequestException during message sending."""
    # Arrange
    service = ChateryService()
    mock_request = MagicMock()
    mock_request.url = "https://fake.chatery.api/messages"

    mock_post = mocker.patch(
        "services.chatery_service.requests.post",
        side_effect=requests.exceptions.RequestException("Request Error", request=mock_request)
    )

    # Act
    with caplog.at_level("ERROR"):
        await service.send_whatsapp_reply("1234567890", "Hello, world!")

    # Assert
    assert "An error occurred while requesting" in caplog.text


@pytest.mark.asyncio
async def test_send_whatsapp_reply_unexpected_error(mocker, set_env_vars, caplog):
    """Test handling unexpected errors during message sending."""
    # Arrange
    service = ChateryService()
    mock_post = mocker.patch(
        "services.chatery_service.requests.post",
        side_effect=Exception("Unexpected error")
    )

    # Act
    with caplog.at_level("ERROR"):
        await service.send_whatsapp_reply("1234567890", "Hello, world!")

    # Assert
    assert "Unexpected error" in caplog.text


def test_verify_webhook_signature_valid(mocker, set_env_vars):
    """Test verifying a valid webhook signature."""
    # Arrange
    import hmac
    import hashlib
    
    service = ChateryService()
    payload = b'{"test": "data"}'
    expected_signature = hmac.new(
        "fake_webhook_secret".encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Act
    result = service.verify_webhook_signature(expected_signature, payload)

    # Assert
    assert result is True


def test_verify_webhook_signature_invalid(mocker, set_env_vars, caplog):
    """Test verifying an invalid webhook signature."""
    # Arrange
    service = ChateryService()
    payload = b'{"test": "data"}'
    invalid_signature = "invalid_signature"

    # Act
    with caplog.at_level("WARNING"):
        result = service.verify_webhook_signature(invalid_signature, payload)

    # Assert
    assert result is False
    assert "Invalid webhook signature" in caplog.text


def test_verify_webhook_signature_no_secret(mocker, monkeypatch, caplog):
    """Test that signature verification is skipped when no secret is configured."""
    # Arrange
    monkeypatch.setenv("CHATERY_API_URL", "https://fake.chatery.api")
    monkeypatch.setenv("CHATERY_API_KEY", "fake_chatery_key")
    monkeypatch.setenv("CHATERY_PHONE_NUMBER_ID", "fake_phone_id")
    monkeypatch.setenv("CHATERY_WEBHOOK_SECRET", "")
    
    service = ChateryService()
    payload = b'{"test": "data"}'

    # Act
    with caplog.at_level("WARNING"):
        result = service.verify_webhook_signature("any_signature", payload)

    # Assert
    assert result is True
    assert "skipping signature verification" in caplog.text


def test_init_missing_api_url(monkeypatch):
    """Test that initialization fails when API URL is missing."""
    # Arrange
    monkeypatch.setenv("CHATERY_API_URL", "")
    monkeypatch.setenv("CHATERY_API_KEY", "fake_key")
    monkeypatch.setenv("CHATERY_PHONE_NUMBER_ID", "fake_id")

    # Act & Assert
    with pytest.raises(ValueError, match="CHATERY_API_URL"):
        ChateryService()


def test_init_missing_api_key(monkeypatch):
    """Test that initialization fails when API key is missing."""
    # Arrange
    monkeypatch.setenv("CHATERY_API_URL", "https://fake.api")
    monkeypatch.setenv("CHATERY_API_KEY", "")
    monkeypatch.setenv("CHATERY_PHONE_NUMBER_ID", "fake_id")

    # Act & Assert
    with pytest.raises(ValueError, match="CHATERY_API_KEY"):
        ChateryService()


def test_init_missing_phone_number_id(monkeypatch):
    """Test that initialization fails when phone number ID is missing."""
    # Arrange
    monkeypatch.setenv("CHATERY_API_URL", "https://fake.api")
    monkeypatch.setenv("CHATERY_API_KEY", "fake_key")
    monkeypatch.setenv("CHATERY_PHONE_NUMBER_ID", "")

    # Act & Assert
    with pytest.raises(ValueError, match="CHATERY_PHONE_NUMBER_ID"):
        ChateryService()
