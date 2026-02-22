# Chatery WhatsApp Integration Setup Guide

This guide explains how to set up and configure the Chatery Cloud API integration for WhatsApp messaging in Cloud Brain.

## Prerequisites

- A Chatery account with WhatsApp Business API access
- A verified WhatsApp Business phone number
- Cloud Brain application deployed and accessible via HTTPS

## Step 1: Chatery Dashboard Setup

### 1.1 Create a WhatsApp Connection

1. Log in to your Chatery dashboard at [https://chatery.com](https://chatery.com)
2. Navigate to **Connections** > **Add New Connection**
3. Select **WhatsApp** as the connection type
4. Choose **Cloud API** as the integration method

### 1.2 Configure Phone Number

1. Select your WhatsApp Business phone number from the list
2. If not connected, follow Chatery's instructions to connect your phone number
3. Wait for the connection status to show as **Active**

### 1.3 Get API Credentials

1. Go to **Settings** > **API** in your Chatery dashboard
2. Generate a new API key if you don't have one
3. Copy the following credentials:
   - **API URL** (e.g., `https://api.chatery.com/v1`)
   - **API Key** (your secret API key)
   - **Phone Number ID** (your WhatsApp phone number ID)

## Step 2: Environment Configuration

### 2.1 Configure Environment Variables

1. Copy the `.env.example` file to `.env` in your Cloud Brain project:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` and fill in the Chatery configuration:
   ```env
   # Chatery Configuration (WhatsApp Cloud API)
   CHATERY_API_URL=https://api.chatery.com/v1
   CHATERY_API_KEY=your_chatery_api_key_here
   CHATERY_PHONE_NUMBER_ID=your_phone_number_id_here
   CHATERY_WEBHOOK_SECRET=your_webhook_secret_here
   ```

3. **Important**: Leave the WAHA configuration empty if you're only using Chatery:
   ```env
   # WAHA Configuration (leave empty if not using)
   WAHA_API_URL=
   WAHA_API_KEY=
   WAHA_SESSION_NAME=
   ```

### 2.2 Configure Whitelisted Numbers

Add the phone numbers that are allowed to interact with the bot:
```env
WHITELISTED_NUMBERS=1234567890,0987654321
```

**Note**: Use international format without the `+` sign.

## Step 3: Webhook Configuration

### 3.1 Set Webhook URL in Chatery

1. In your Chatery dashboard, go to **Connections** > **Your WhatsApp Connection** > **Webhooks**
2. Click **Add Webhook**
3. Enter your Cloud Brain webhook URL:
   ```
   https://your-domain.com/chatery/webhook
   ```
4. Select the following events to subscribe to:
   - **Messages** (incoming messages)
   - **Message Status** (delivery receipts, read receipts)

### 3.2 Configure Webhook Secret

1. Generate a secure random string for your webhook secret (at least 32 characters)
2. Add it to your `.env` file:
   ```env
   CHATERY_WEBHOOK_SECRET=your_secure_random_string_here
   ```
3. Enter the same secret in the Chatery dashboard webhook configuration

### 3.3 Verify Webhook

Chatery will send a verification request to your webhook URL. The application will automatically respond with the challenge token if the verify token matches.

## Step 4: Testing

### 4.1 Verify Application Startup

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
   ChateryService initialized with API URL: https://api.chatery.com/v1 and phone number ID: your_phone_number_id
   ```

### 4.2 Test Webhook Connection

1. In the Chatery dashboard, check the webhook status
2. It should show as **Active** or **Connected**
3. Send a test message from your WhatsApp to trigger the webhook

### 4.3 Test Message Flow

1. Send a message from a whitelisted number to your WhatsApp Business number
2. Check the application logs for:
   ```
   Message from <number>: <message_body>
   Identified message type: <type>
   ```
3. Verify that you receive a response on WhatsApp

### 4.4 Test Commands

- **Sync Command**: Send a message that triggers SYNC type identification to start database synchronization
- **Query Command**: Send a question to test the RAG (Retrieval-Augmented Generation) functionality

## Step 5: Switching Between WAHA and Chatery

### Using Chatery Only

```env
# Chatery Configuration (filled)
CHATERY_API_URL=https://api.chatery.com/v1
CHATERY_API_KEY=your_key
CHATERY_PHONE_NUMBER_ID=your_id
CHATERY_WEBHOOK_SECRET=your_secret

# WAHA Configuration (empty)
WAHA_API_URL=
WAHA_API_KEY=
WAHA_SESSION_NAME=
```

### Using WAHA Only

```env
# Chatery Configuration (empty)
CHATERY_API_URL=
CHATERY_API_KEY=
CHATERY_PHONE_NUMBER_ID=
CHATERY_WEBHOOK_SECRET=

# WAHA Configuration (filled)
WAHA_API_URL=http://localhost:3000
WAHA_API_KEY=your_waha_key
WAHA_SESSION_NAME=your_session
```

### Using Both (Different Endpoints)

Both integrations can run simultaneously with different webhook URLs:
- WAHA: `https://your-domain.com/waha/webhook`
- Chatery: `https://your-domain.com/chatery/webhook`

Configure different phone numbers for each integration.

## Troubleshooting

### Webhook Not Receiving Messages

1. Verify your webhook URL is accessible from the internet (use HTTPS)
2. Check that the webhook secret matches in both `.env` and Chatery dashboard
3. Review application logs for any errors
4. Test webhook endpoint manually:
   ```bash
   curl -X GET "https://your-domain.com/chatery/webhook?hub.mode=subscribe&hub.verify_token=your_secret&hub.challenge=12345"
   ```

### Messages Not Being Sent

1. Verify `CHATERY_API_URL` and `CHATERY_API_KEY` are correct
2. Check that `CHATERY_PHONE_NUMBER_ID` is valid
3. Review application logs for API error responses
4. Test API connection manually:
   ```bash
   curl -X POST "https://api.chatery.com/v1/messages" \
     -H "Authorization: Bearer your_api_key" \
     -H "Content-Type: application/json" \
     -d '{"messaging_product":"whatsapp","to":"1234567890","type":"text","text":{"body":"test"}}'
   ```

### Unauthorized Access Warnings

1. Ensure sender numbers are in the `WHITELISTED_NUMBERS` environment variable
2. Check that numbers are in international format without `+`
3. Verify no extra spaces in the comma-separated list

## API Reference

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chatery/webhook` | GET | Webhook verification |
| `/chatery/webhook` | POST | Receive incoming messages |

### Webhook Payload Format

Chatery sends messages in the following format:
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "messages": [{
          "from": "1234567890",
          "type": "text",
          "text": {
            "body": "Hello"
          }
        }]
      }
    }]
  }]
}
```

## Security Best Practices

1. **Keep API keys secret**: Never commit `.env` to version control
2. **Use HTTPS**: Always use HTTPS for webhook URLs in production
3. **Verify webhooks**: Always enable webhook signature verification
4. **Limit whitelisted numbers**: Only allow trusted numbers to interact
5. **Rotate secrets**: Periodically rotate API keys and webhook secrets

## Support

For Chatery-specific issues, refer to:
- [Chatery Documentation](https://docs.chatery.com/)
- [Chatery Support](https://chatery.com/support)

For Cloud Brain integration issues, check the application logs and README.md.
