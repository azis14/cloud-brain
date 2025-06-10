# Cloud Brain
[![codecov](https://codecov.io/github/azis14/cloud-brain/graph/badge.svg?token=JLIHMRS0QW)](https://codecov.io/github/azis14/cloud-brain)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

A FastAPI application that connects to the Notion API and provides RAG (Retrieval-Augmented Generation) capabilities using MongoDB Atlas Vector Search and Google AI Studio.

## Features

### Notion Integration
- 🔗 Connect to Notion API
- 📊 Fetch data from Notion databases
- 📋 Simplified data extraction

### RAG & Vector Search
- 🧠 Sync Notion content to MongoDB Atlas as vector embeddings
- 🔍 Vector similarity search using sentence transformers
- 🤖 Question answering with Google AI Studio (Gemini)
- 💬 Chat interface for natural language queries

## Setup

### 1. Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
# Notion API Configuration
NOTION_API_KEY=your_notion_integration_token_here
NOTION_DATABASE_IDS=your_comma_separated_database_ids_here

# MongoDB Atlas Configuration
MONGODB_URI=your_url_to_mongodb_atlas_cluster_here
MONGODB_DATABASE=your_database_name_here
MONGODB_COLLECTION=your_collection_name_here

# Google AI Studio Configuration
GOOGLE_API_KEY=your_google_ai_studio_api_key (optional, could use another LLM)
GOOGLE_MODEL=(gemini-1.5-flash or other model)

# Vector Database Configuration (Optional - defaults provided)
EMBEDDING_MODEL=all-MiniLM-L6-v2
MAX_CHUNK_TOKENS=500
CHUNK_OVERLAP_TOKENS=50
MAX_CONTEXT_CHUNKS=5
MIN_SIMILARITY_SCORE=0.7

# Other Configurations
CORS_ALLOW_ORIGINS=could be '*' or specific origins here
API_SECRET_KEY=generate_random_string_here
```

### 2. MongoDB Atlas Setup

1. Create a MongoDB Atlas cluster
2. Create a database
3. Create a collection
4. **Important**: Create a vector search index:
   - Index name: `vector_index`
   - Field path: `embedding`
   - Dimensions: `384` (for all-MiniLM-L6-v2 model)
   - Similarity: `cosine`

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Interactive API docs**: `http://localhost:8000/docs`
- **ReDoc documentation**: `http://localhost:8000/redoc`

## Notion Integration Setup

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click "New integration"
3. Give it a name and select your workspace
4. Copy the "Internal Integration Token" - this is your `NOTION_API_KEY`
5. Share your databases with the integration:
   - Open the database in Notion
   - Click "Share" → "Invite"
   - Search for your integration name and invite it

## Property Types Supported

The API handles all Notion property types:

- **Text**: `title`, `rich_text`
- **Numbers**: `number`
- **Selections**: `select`, `multi_select`
- **Dates**: `date`
- **People**: `people`
- **Files**: `files`
- **Checkboxes**: `checkbox`
- **URLs**: `url`
- **Email**: `email`
- **Phone**: `phone_number`
- **Relations**: `relation`
- **Timestamps**: `created_time`, `last_edited_time`
- **Users**: `created_by`, `last_edited_by`

## Filter Types

Available filter types for the simplified query endpoint:

### Text Filters
- `equals`, `does_not_equal`
- `contains`, `does_not_contain`
- `starts_with`, `ends_with`
- `is_empty`, `is_not_empty`

### Number Filters
- `equals`, `does_not_equal`
- `greater_than`, `less_than`
- `greater_than_or_equal_to`, `less_than_or_equal_to`

### Date Filters
- `equals`, `before`, `after`
- `on_or_before`, `on_or_after`

### Checkbox Filters
- `checkbox_equals`

## Error Handling

The API includes comprehensive error handling:
- Invalid database IDs return 404
- Missing environment variables raise startup errors
- Notion API errors are properly propagated
- All endpoints include try-catch blocks with logging

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when test files are created)
pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-E5E5E5?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://clicky.id/azis14/support/coffee)
[![More About Me](https://img.shields.io/badge/More%20About%20Me-E5E5E5?style=for-the-badge&logo=about.me&logoColor=black)](https://www.azis14.my.id/)
