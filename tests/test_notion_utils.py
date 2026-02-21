import pytest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from utils.notion_utils import NotionUtils

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def mock_async_client():
    return AsyncMock()

@pytest.fixture
def notion_utils(mock_client):
    return NotionUtils(mock_client)

@pytest.fixture
def notion_utils_async(mock_async_client):
    return NotionUtils(mock_async_client)

# ==================== Page Property Extraction Tests ====================

def test_extract_page_properties_title_and_rich_text(notion_utils):
    page = {
        "properties": {
            "Title": {"type": "title", "title": [{"plain_text": "Hello"}]},
            "Description": {"type": "rich_text", "rich_text": [{"plain_text": "World"}]},
            "Number": {"type": "number", "number": 42},
            "Select": {"type": "select", "select": {"name": "Option1"}},
            "MultiSelect": {"type": "multi_select", "multi_select": [{"name": "A"}, {"name": "B"}]},
            "Date": {"type": "date", "date": {"start": "2024-01-01", "end": "2024-01-02"}},
            "Checkbox": {"type": "checkbox", "checkbox": True},
            "Url": {"type": "url", "url": "https://example.com"},
            "Email": {"type": "email", "email": "test@example.com"},
            "Phone": {"type": "phone_number", "phone_number": "123456"},
            "Relation": {"type": "relation", "relation": [{"id": "abc"}]},
            "People": {"type": "people", "people": [{"id": "user1", "name": "John"}]},
            "Files": {"type": "files", "files": [{"type": "file", "name": "file1", "file": {"url": "url1"}}]},
            "CreatedTime": {"type": "created_time", "created_time": "2024-01-01T00:00:00Z"},
            "LastEditedTime": {"type": "last_edited_time", "last_edited_time": "2024-01-02T00:00:00Z"},
            "CreatedBy": {"type": "created_by", "created_by": {"id": "creator", "name": "Creator"}},
            "LastEditedBy": {"type": "last_edited_by", "last_edited_by": {"id": "editor", "name": "Editor"}},
            "Unknown": {"type": "unknown", "foo": "bar"}
        }
    }
    props = notion_utils.extract_page_properties(page)
    assert props["Title"] == "Hello"
    assert props["Description"] == "World"
    assert props["Number"] == 42
    assert props["Select"] == "Option1"
    assert props["MultiSelect"] == ["A", "B"]
    assert props["Date"] == {"start": "2024-01-01", "end": "2024-01-02"}
    assert props["Checkbox"] is True
    assert props["Url"] == "https://example.com"
    assert props["Email"] == "test@example.com"
    assert props["Phone"] == "123456"
    assert props["Relation"] == ["abc"]
    assert props["People"] == ["John"]
    assert props["Files"][0]["name"] == "file1"
    assert props["Files"][0]["url"] == "url1"
    assert props["CreatedTime"] == "2024-01-01T00:00:00Z"
    assert props["LastEditedTime"] == "2024-01-02T00:00:00Z"
    assert props["CreatedBy"] == "Creator"
    assert props["LastEditedBy"] == "Editor"
    assert props["Unknown"]["foo"] == "bar"

def test_extract_page_properties_formula_and_rollup(notion_utils):
    page = {
        "properties": {
            "Formula": {"type": "formula", "formula": {"string": "Result", "number": 123}},
            "Rollup": {"type": "rollup", "rollup": {"type": "string", "string": "Rolled value"}}
        }
    }
    props = notion_utils.extract_page_properties(page)
    assert props["Formula"] == "Result"
    assert props["Rollup"] == "Rolled value"

# ==================== Rich Text Extraction Tests ====================

def test_extract_rich_text(notion_utils):
    rich_text = [{"plain_text": "Hello, "}, {"plain_text": "world!"}]
    assert notion_utils._extract_rich_text(rich_text) == "Hello, world!"
    assert notion_utils._extract_rich_text([]) == ""

def test_extract_rich_text_with_mentions(notion_utils):
    rich_text = [
        {"type": "text", "plain_text": "Hello "},
        {
            "type": "mention",
            "plain_text": "@John",
            "mention": {"type": "user", "user": {"name": "John"}}
        },
        {"type": "text", "plain_text": " check this "},
        {
            "type": "mention",
            "plain_text": "[Page]",
            "mention": {"type": "page", "page": {"id": "page123"}}
        }
    ]
    result = notion_utils._extract_rich_text(rich_text)
    assert "@John" in result
    assert "[Page: page123]" in result

# ==================== Block Content Extraction Tests ====================

def test_extract_block_content_paragraph(notion_utils):
    block = {
        "id": "block1",
        "type": "paragraph",
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-01T00:00:00Z",
        "has_children": False,
        "paragraph": {"rich_text": [{"plain_text": "Paragraph text"}]}
    }
    content = notion_utils.extract_block_content(block)
    assert content["id"] == "block1"
    assert content["type"] == "paragraph"
    assert content["text"] == "Paragraph text"

def test_extract_block_content_heading(notion_utils):
    block = {
        "id": "block2",
        "type": "heading_1",
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-01T00:00:00Z",
        "has_children": False,
        "heading_1": {"rich_text": [{"plain_text": "Heading"}]}
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "heading_1"
    assert content["text"] == "Heading"
    assert content["level"] == 1

def test_extract_block_content_table_row(notion_utils):
    block = {
        "id": "table_row_1",
        "type": "table_row",
        "table_row": {
            "cells": [
                [{"plain_text": "Cell 1"}],
                [{"plain_text": "Cell 2"}],
                [{"plain_text": "Cell 3"}]
            ]
        }
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "table_row"
    assert content["cells"] == ["Cell 1", "Cell 2", "Cell 3"]

def test_extract_block_content_code(notion_utils):
    block = {
        "id": "code_block",
        "type": "code",
        "code": {
            "rich_text": [{"plain_text": "print('Hello')"}],
            "language": "python"
        }
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "code"
    assert content["text"] == "print('Hello')"
    assert content["language"] == "python"
    assert content["is_code"] is True

def test_extract_block_content_toggle(notion_utils):
    block = {
        "id": "toggle_block",
        "type": "toggle",
        "toggle": {
            "rich_text": [{"plain_text": "Toggle summary"}]
        }
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "toggle"
    assert content["text"] == "Toggle summary"
    assert content["is_toggle"] is True

def test_extract_block_content_child_page(notion_utils):
    block = {
        "id": "child_page_id",
        "type": "child_page",
        "child_page": {"title": "Child Page Title"}
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "child_page"
    assert content["title"] == "Child Page Title"
    assert content["child_page_id"] == "child_page_id"

def test_extract_block_content_equation(notion_utils):
    block = {
        "id": "eq_block",
        "type": "equation",
        "equation": {"expression": "E = mc^2"}
    }
    content = notion_utils.extract_block_content(block)
    assert content["type"] == "equation"
    assert content["expression"] == "E = mc^2"
    assert content["is_equation"] is True

def test_extract_block_content_synced_block_dedup(notion_utils):
    # First synced block with an ID
    block1 = {
        "id": "sync1",
        "type": "synced_block",
        "synced_block": {"synced_from": {"id": "original_123"}}
    }
    # Second synced block referencing same ID
    block2 = {
        "id": "sync2",
        "type": "synced_block",
        "synced_block": {"synced_from": {"id": "original_123"}}
    }
    
    content1 = notion_utils.extract_block_content(block1)
    content2 = notion_utils.extract_block_content(block2)
    
    assert content1.get("skipped") is None  # First one should not be skipped
    assert content2.get("skipped") is True  # Second one should be skipped

# ==================== Markdown Conversion Tests ====================

def test_blocks_to_markdown_headings(notion_utils):
    blocks = [
        {"type": "heading_1", "text": "Main Title", "level": 1},
        {"type": "heading_2", "text": "Subtitle", "level": 2},
        {"type": "heading_3", "text": "Subsection", "level": 3}
    ]
    markdown = notion_utils.blocks_to_markdown(blocks, include_metadata=False)
    assert "# Main Title" in markdown
    assert "## Subtitle" in markdown
    assert "### Subsection" in markdown

def test_blocks_to_markdown_lists(notion_utils):
    blocks = [
        {"type": "bulleted_list_item", "text": "Item 1"},
        {"type": "bulleted_list_item", "text": "Item 2"},
        {"type": "numbered_list_item", "text": "Numbered 1"},
        {"type": "numbered_list_item", "text": "Numbered 2"}
    ]
    markdown = notion_utils.blocks_to_markdown(blocks, include_metadata=False)
    assert "- Item 1" in markdown
    assert "- Item 2" in markdown
    assert "1. Numbered 1" in markdown
    assert "2. Numbered 2" in markdown

def test_blocks_to_markdown_todo(notion_utils):
    blocks = [
        {"type": "to_do", "text": "Task 1", "checked": True},
        {"type": "to_do", "text": "Task 2", "checked": False}
    ]
    markdown = notion_utils.blocks_to_markdown(blocks, include_metadata=False)
    assert "- [x] Task 1" in markdown
    assert "- [ ] Task 2" in markdown

def test_blocks_to_markdown_code(notion_utils):
    blocks = [
        {"type": "code", "text": "print('Hello')", "language": "python", "is_code": True}
    ]
    markdown = notion_utils.blocks_to_markdown(blocks, include_metadata=False)
    assert "```python" in markdown
    assert "print('Hello')" in markdown
    assert "```" in markdown

def test_blocks_to_markdown_quote(notion_utils):
    blocks = [
        {"type": "quote", "text": "This is a quote", "is_quote": True}
    ]
    markdown = notion_utils.blocks_to_markdown(blocks, include_metadata=False)
    assert "> This is a quote" in markdown

def test_blocks_to_markdown_with_metadata(notion_utils):
    metadata = {
        "title": "Test Page",
        "properties": {"Status": "Done", "Tags": ["important", "test"]},
        "url": "https://notion.so/test"
    }
    blocks = [{"type": "paragraph", "text": "Content"}]
    markdown = notion_utils.blocks_to_markdown(blocks, page_metadata=metadata)
    assert "# Test Page" in markdown
    assert "- **Status**: Done" in markdown
    assert "- **Tags**: important, test" in markdown

# ==================== Text Extraction for Embedding Tests ====================

def test_extract_text_for_embedding(notion_utils):
    page_data = {
        "properties": {
            "title": "Test Document",
            "Status": "Active",
            "Category": "Testing"
        },
        "markdown_content": "# Content\nThis is the main content."
    }
    text = notion_utils.extract_text_for_embedding(page_data)
    assert "Title: Test Document" in text
    assert "Status: Active" in text
    assert "Category: Testing" in text
    assert "Content" in text
    assert "main content" in text

def test_clean_markdown_for_embedding(notion_utils):
    markdown = """# Header
## Subheader
- List item 1
- List item 2
1. Numbered 1
2. Numbered 2
```python
code block
```
> Quote here
"""
    cleaned = notion_utils._clean_markdown_for_embedding(markdown)
    assert "Header" in cleaned
    assert "Subheader" in cleaned
    assert "List item" in cleaned
    assert "```" not in cleaned
    assert ">" not in cleaned

# ==================== Database Schema Tests ====================

@pytest.mark.asyncio
async def test_get_database_schema(notion_utils_async, mock_async_client):
    mock_async_client.databases.retrieve = AsyncMock(return_value={
        "title": [{"plain_text": "Test DB"}],
        "properties": {
            "Status": {
                "type": "select",
                "id": "status",
                "select": {"options": [{"name": "A"}, {"name": "B"}]}
            },
            "Tags": {
                "type": "multi_select",
                "id": "tags",
                "multi_select": {"options": [{"name": "X"}, {"name": "Y"}]}
            },
            "Amount": {
                "type": "number",
                "id": "amount",
                "number": {"format": "dollar"}
            },
            "Related": {
                "type": "relation",
                "id": "rel",
                "relation": {"database_id": "db123"}
            }
        },
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-02T00:00:00Z",
        "url": "https://notion.so/db"
    })
    schema = await notion_utils_async.get_database_schema("dbid")
    assert schema["title"] == "Test DB"
    assert schema["properties"]["Status"]["options"] == ["A", "B"]
    assert schema["properties"]["Tags"]["options"] == ["X", "Y"]
    assert schema["properties"]["Amount"]["format"] == "dollar"
    assert schema["properties"]["Related"]["relation_database_id"] == "db123"
    assert schema["created_time"] == "2024-01-01T00:00:00Z"
    assert schema["last_edited_time"] == "2024-01-02T00:00:00Z"
    assert schema["url"] == "https://notion.so/db"

def test_build_filter(notion_utils):
    f = notion_utils.build_filter("Status", "equals", "Done")
    assert f == {"property": "Status", "equals": {"equals": "Done"}}
    with pytest.raises(ValueError):
        notion_utils.build_filter("Status", "unsupported", "Done")

def test_build_sort(notion_utils):
    s = notion_utils.build_sort("Created", "ascending")
    assert s == {"property": "Created", "direction": "ascending"}
    s = notion_utils.build_sort("Created", "descending")
    assert s == {"property": "Created", "direction": "descending"}
    with pytest.raises(ValueError):
        notion_utils.build_sort("Created", "invalid")

# ==================== Async Tests ====================

@pytest.mark.asyncio
async def test_fetch_all_blocks_recursive(notion_utils_async):
    # Mock the blocks.children.list response
    mock_response = {
        "results": [
            {
                "id": "block1",
                "type": "paragraph",
                "has_children": False,
                "paragraph": {"rich_text": [{"plain_text": "Test"}]}
            }
        ],
        "has_more": False,
        "next_cursor": None
    }
    notion_utils_async.client.blocks.children.list = AsyncMock(return_value=mock_response)
    
    blocks = await notion_utils_async.fetch_all_blocks_recursive("page123")
    
    assert len(blocks) == 1
    assert blocks[0]["id"] == "block1"
    assert blocks[0]["text"] == "Test"

@pytest.mark.asyncio
async def test_fetch_child_page_content(notion_utils_async):
    # Mock page retrieve
    mock_page = {
        "id": "child123",
        "url": "https://notion.so/child",
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-01T00:00:00Z",
        "properties": {
            "title": {"type": "title", "title": [{"plain_text": "Child Page"}]}
        }
    }
    notion_utils_async.client.pages.retrieve = AsyncMock(return_value=mock_page)
    
    # Mock blocks fetch (return empty)
    notion_utils_async.client.blocks.children.list = AsyncMock(return_value={
        "results": [],
        "has_more": False
    })
    
    page_data = await notion_utils_async.fetch_child_page_content("child123")
    
    assert page_data["id"] == "child123"
    assert page_data["url"] == "https://notion.so/child"
    # Check cache was populated
    assert "child123" in notion_utils_async._page_cache

@pytest.mark.asyncio
async def test_extract_complete_page_data(notion_utils_async):
    # Mock page retrieve
    mock_page = {
        "id": "page123",
        "url": "https://notion.so/page",
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-01T00:00:00Z",
        "properties": {
            "title": {"type": "title", "title": [{"plain_text": "Test Page"}]}
        }
    }
    notion_utils_async.client.pages.retrieve = AsyncMock(return_value=mock_page)
    
    # Mock blocks fetch
    notion_utils_async.client.blocks.children.list = AsyncMock(return_value={
        "results": [
            {
                "id": "block1",
                "type": "paragraph",
                "has_children": False,
                "paragraph": {"rich_text": [{"plain_text": "Content here"}]}
            }
        ],
        "has_more": False
    })
    
    page_data = await notion_utils_async.extract_complete_page_data("page123")
    
    assert page_data["id"] == "page123"
    assert page_data["properties"]["title"] == "Test Page"
    assert len(page_data["blocks"]) == 1
    assert "markdown_content" in page_data
