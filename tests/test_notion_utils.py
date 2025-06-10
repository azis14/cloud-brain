import pytest
from unittest.mock import MagicMock
from utils.notion_utils import NotionUtils

@pytest.fixture
def mock_client():
    return MagicMock()

@pytest.fixture
def notion_utils(mock_client):
    return NotionUtils(mock_client)

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
            "People": {"type": "people", "people": [{"id": "user1"}]},
            "Files": {"type": "files", "files": [{"type": "file", "name": "file1", "file": {"url": "url1"}}]},
            "CreatedTime": {"type": "created_time", "created_time": "2024-01-01T00:00:00Z"},
            "LastEditedTime": {"type": "last_edited_time", "last_edited_time": "2024-01-02T00:00:00Z"},
            "CreatedBy": {"type": "created_by", "created_by": {"id": "creator"}},
            "LastEditedBy": {"type": "last_edited_by", "last_edited_by": {"id": "editor"}},
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
    assert props["People"] == ["user1"]
    assert props["Files"][0]["name"] == "file1"
    assert props["Files"][0]["url"] == "url1"
    assert props["CreatedTime"] == "2024-01-01T00:00:00Z"
    assert props["LastEditedTime"] == "2024-01-02T00:00:00Z"
    assert props["CreatedBy"] == "creator"
    assert props["LastEditedBy"] == "editor"
    assert props["Unknown"]["foo"] == "bar"

def test_extract_rich_text(notion_utils):
    rich_text = [{"plain_text": "Hello, "}, {"plain_text": "world!"}]
    assert notion_utils._extract_rich_text(rich_text) == "Hello, world!"
    assert notion_utils._extract_rich_text([]) == ""

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

def test_get_database_schema(notion_utils, mock_client):
    mock_client.databases.retrieve.return_value = {
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
            }
        },
        "created_time": "2024-01-01T00:00:00Z",
        "last_edited_time": "2024-01-02T00:00:00Z"
    }
    schema = notion_utils.get_database_schema("dbid")
    assert schema["title"] == "Test DB"
    assert schema["properties"]["Status"]["options"] == ["A", "B"]
    assert schema["properties"]["Tags"]["options"] == ["X", "Y"]
    assert schema["properties"]["Amount"]["format"] == "dollar"
    assert schema["created_time"] == "2024-01-01T00:00:00Z"
    assert schema["last_edited_time"] == "2024-01-02T00:00:00Z"

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