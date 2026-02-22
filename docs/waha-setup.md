# WAHA (WhatsApp HTTP API) Integration Setup Guide

This guide explains how to set up and configure WAHA for WhatsApp messaging in Cloud Brain.

## Prerequisites

- Docker installed (recommended) OR direct installation environment
- A WhatsApp Business phone number
- Cloud Brain application deployed and accessible via HTTPS

## Step 1: WAHA Installation

### Option 1: Docker Installation (Recommended)

1. Pull the WAHA Docker image:
   ```bash
   docker pull devlikeapro/waha:latest
   ```

2. Create a Docker network for WAHA:
   ```bash
   docker network create waha-network
   ```

3. Run WAHA container:
   ```bash
   docker run -d \
     --name waha \
     --network waha-network \
     -p 3000:3000 \
     -e WAHA_SESSIONS=default \
     -e WEBHOOK_URL=http://your-domain.com/waha/webhook \
     devlikeapro/waha:latest
   ```

4. Verify the container is running:
   ```bash
   docker ps | grep waha
   ```

### Option 2: Direct Installation

1. Clone the WAHA repository:
   ```bash
   git clone https://github.com/devlikeapro/waha.git
   cd waha
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure WAHA:
   ```bash
   cp .env.example .env
   ```

4. Start WAHA:
   ```bash
   npm start
   ```

## Step 2: WAHA Session Configuration

### 2.1 Create a Session

1. Access the WAHA dashboard at `http://localhost:3000`
2. Navigate to **Sessions** > **Add Session**
3. Name your session (e.g., `cloud-brain`)
4. Select the connection type (WhatsApp Web)

### 2.2 Connect WhatsApp

1. In the WAHA dashboard, select your session
2. Click **Connect** or **Start**
3. Scan the QR code with your WhatsApp mobile app:
   - Open WhatsApp on your phone
   - Go to **Settings** > **Linked Devices**
   - Tap **Link a Device**
   - Scan the QR code

4. Wait for the connection status to show as **Connected**

### 2.3 Get Session Details

1. Note the session name you configured
2. Generate an API key if required
3. Note the WAHA API URL (e.g., `http://localhost:3000` or `https://waha.your-domain.com`)

## Step 3: Environment Configuration

### 3.1 Configure Environment Variables

1. Copy the `.env.example` file to `.env` in your Cloud Brain project:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in the WAHA configuration:
   ```env
   # WAHA Configuration
   WAHA_API_URL=http://localhost:3000
   WAHA_API_KEY=your_waha_api_key_here
   WAHA_SESSION_NAME=cloud-brain

   # Chatery Configuration (leave empty if not using)
   CHATERY_API_URL=
   CHATERY_API_KEY=
   CHATERY_PHONE_NUMBER_ID=
   CHATERY_WEBHOOK_SECRET=
   ```

### 3.2 Configure Whitelisted Numbers

Add the phone numbers that are allowed to interact with the bot:
```env
WHITELISTED_NUMBERS=1234567890,0987654321
```

**Note**: Use international format without the `+` sign.

## Step 4: Webhook Configuration

### 4.1 Set Webhook URL in WAHA

1. Access the WAHA dashboard
2. Navigate to **Sessions** > **Your Session** > **Webhooks**
3. Add a new webhook:
   ```
   https://your-domain.com/waha/webhook
   ```
4. Select events to subscribe to:
   - **message** (incoming messages)
   - **status** (message status updates)

### 4.2 Configure Webhook via API

Alternatively, configure the webhook using WAHA's API:
```bash
curl -X POST "http://localhost:3000/webhook" \
  -H "X-Api-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "session": "cloud-brain",
    "webhook": "https://your-domain.com/waha/webhook",
    "events": ["message"]
  }'
```

## Step 5: Testing

### 5.1 Verify Application Startup

1. Start your Cloud Brain application:
   ```bash
   python main.py
   ```
   or with uvicorn:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Check the logs for:
   ```
   WahaService initialized with API URL: http://localhost:3000 and session name: cloud-brain
   ```

### 5.2 Test WAHA Connection

1. Test WAHA API directly:
   ```bash
   curl "http://localhost:3000/sessions" \
     -H "X-Api-Key: your_api_key"
   ```

2. Verify the session is listed and connected

### 5.3 Test Message Flow

1. Send a message from a whitelisted number to your WhatsApp
2. Check the application logs for:
   ```
   Message from <number>: <message_body>
   Identified message type: <type>
   ```
3. Verify that you receive a response on WhatsApp

### 5.4 Test Commands

- **Sync Command**: Send a message that triggers SYNC type identification to start database synchronization
- **Query Command**: Send a question to test the RAG (Retrieval-Augmented Generation) functionality

## Step 6: Switching Between WAHA and Chatery

### Using WAHA Only

```env
# WAHA Configuration (filled)
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=your_waha_key
WAHA_SESSION_NAME=cloud-brain

# Chatery Configuration (empty)
CHATERY_API_URL=
CHATERY_API_KEY=
CHATERY_PHONE_NUMBER_ID=
CHATERY_WEBHOOK_SECRET=
```

### Using Chatery Only

```env
# WAHA Configuration (empty)
WAHA_API_URL=
WAHA_API_KEY=
WAHA_SESSION_NAME=

# Chatery Configuration (filled)
CHATERY_API_URL=https://api.chatery.com/v1
CHATERY_API_KEY=your_key
CHATERY_PHONE_NUMBER_ID=your_id
CHATERY_WEBHOOK_SECRET=your_secret
```

### Using Both (Different Endpoints)

Both integrations can run simultaneously with different webhook URLs:
- WAHA: `https://your-domain.com/waha/webhook`
- Chatery: `https://your-domain.com/chatery/webhook`

Configure different phone numbers for each integration.

## Troubleshooting

### Session Disconnected

1. Check the WAHA dashboard for session status
2. Re-scan the QR code if the session expired
3. Restart the WAHA container:
   ```bash
   docker restart waha
   ```

### Webhook Not Receiving Messages

1. Verify your webhook URL is accessible from the internet (use HTTPS)
2. Check WAHA webhook configuration in the dashboard
3. Review WAHA logs for webhook delivery errors:
   ```bash
   docker logs waha
   ```
4. Test webhook endpoint manually:
   ```bash
   curl -X POST "https://your-domain.com/waha/webhook" \
     -H "Content-Type: application/json" \
     -d '{"event":"message","payload":{"from":"1234567890@c.us","body":"test"}}'
   ```

### Messages Not Being Sent

1. Verify `WAHA_API_URL` is correct and accessible
2. Check that `WAHA_API_KEY` is valid
3. Ensure `WAHA_SESSION_NAME` matches your configured session
4. Test WAHA send API directly:
   ```bash
   curl -X POST "http://localhost:3000/sendText" \
     -H "X-Api-Key: your_api_key" \
     -H "Content-Type: application/json" \
     -d '{
       "session": "cloud-brain",
       "chatId": "1234567890@c.us",
       "text": "test"
     }'
   ```

### Unauthorized Access Warnings

1. Ensure sender numbers are in the `WHITELISTED_NUMBERS` environment variable
2. Check that numbers are in international format without `+`
3. Verify no extra spaces in the comma-separated list

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/waha/webhook` | POST | Receive incoming messages |

### Webhook Payload Format

WAHA sends messages in the following format:
```json
{
  "event": "message",
  "payload": {
    "from": "1234567890@c.us",
    "body": "Hello"
  }
}
```

### WAHA API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sessions` | GET | List all sessions |
| `/sendText` | POST | Send text message |
| `/sendFile` | POST | Send file message |

## Security Best Practices

1. **Keep API keys secret**: Never commit `.env` to version control
2. **Use HTTPS**: Always use HTTPS for webhook URLs in production
3. **Limit whitelisted numbers**: Only allow trusted numbers to interact
4. **Session management**: Regularly check session status and reconnect if needed
5. **Rate limiting**: Be aware of WhatsApp rate limits to avoid bans

## Docker Compose Example

For easy deployment, use Docker Compose:

```yaml
version: '3.8'

services:
  waha:
    image: devlikeapro/waha:latest
    container_name: waha
    ports:
      - "3000:3000"
    environment:
      - WAHA_SESSIONS=default
      - WEBHOOK_URL=http://your-domain.com/waha/webhook
    networks:
      - waha-network
    restart: unless-stopped

  cloud-brain:
    build: .
    container_name: cloud-brain
    ports:
      - "8000:8000"
    environment:
      - WAHA_API_URL=http://waha:3000
      - WAHA_API_KEY=your_api_key
      - WAHA_SESSION_NAME=default
    depends_on:
      - waha
    networks:
      - waha-network
    restart: unless-stopped

networks:
  waha-network:
    driver: bridge
```

## Support

For WAHA-specific issues, refer to:
- [WAHA Documentation](https://waha.devlike.pro/)
- [WAHA GitHub](https://github.com/devlikeapro/waha)

For Cloud Brain integration issues, check the application logs and README.md.
