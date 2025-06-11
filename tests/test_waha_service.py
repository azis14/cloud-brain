import pytest
from unittest.mock import MagicMock
from services.waha_service import WahaService
import requests
import os
import asyncio


@pytest.fixture
def set_env_vars(monkeypatch):
    """Fixture to set environment variables for tests."""
    monkeypatch.setenv("WAHA_API_URL", "https://fake.api.url")
    monkeypatch.setenv("WAHA_API_KEY", "fakeapikey")
    monkeypatch.setenv("WAHA_SESSION_NAME", "fakesession")


@pytest.mark.asyncio
async def test_send_whatsapp_reply_success(mocker, set_env_vars):
    """Test successful message sending."""
    # Arrange
    service = WahaService()
    mock_post = mocker.patch("waha_service.requests.post")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    # Act
    await service.send_whatsapp_reply("recipient_id", "Hello, world!")


@pytest.mark.asyncio
async def test_send_whatsapp_reply_http_error(mocker, set_env_vars, caplog):
    """Test handling HTTP errors during message sending."""
    # Arrange
    service = WahaService()
    mock_post = mocker.patch("waha_service.requests.post")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=MagicMock(text="HTTP Error")
    )
    mock_post.return_value = mock_response

    # Act
    with caplog.at_level("ERROR"):
        await service.send_whatsapp_reply("recipient_id", "Hello, world!")


@pytest.mark.asyncio
async def test_send_whatsapp_reply_request_error(mocker, set_env_vars, caplog):
    """Test handling RequestException during message sending."""
    # Arrange
    service = WahaService()
    mock_request = MagicMock()
    mock_request.url = "https://fake.api.url/sendText"

    mock_post = mocker.patch(
        "waha_service.requests.post",
        side_effect=requests.exceptions.RequestException("Request Error", request=mock_request)
    )

    # Act
    with caplog.at_level("ERROR"):
        await service.send_whatsapp_reply("recipient_id", "Hello, world!")

