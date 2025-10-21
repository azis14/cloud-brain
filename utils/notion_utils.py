from typing import Dict, List, Any
from notion_client import Client
import logging

logger = logging.getLogger(__name__)

class NotionUtils:
    """Utility class for common Notion operations"""
    
    def __init__(self, client: Client):
        self.client = client
    
    def extract_page_properties(self, page: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and simplify page properties for easier consumption"""
        properties = page.get("properties", {})
        extracted = {}
        
        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type")
            
            try:
                if prop_type == "title":
                    extracted[prop_name] = self._extract_rich_text(prop_data.get("title", []))
                elif prop_type == "rich_text":
                    extracted[prop_name] = self._extract_rich_text(prop_data.get("rich_text", []))
                elif prop_type == "number":
                    extracted[prop_name] = prop_data.get("number")
                elif prop_type == "select":
                    select_data = prop_data.get("select")
                    extracted[prop_name] = select_data.get("name") if select_data else None
                elif prop_type == "multi_select":
                    multi_select_data = prop_data.get("multi_select", [])
                    extracted[prop_name] = [item.get("name") for item in multi_select_data]
                elif prop_type == "date":
                    date_data = prop_data.get("date")
                    if date_data:
                        extracted[prop_name] = {
                            "start": date_data.get("start"),
                            "end": date_data.get("end")
                        }
                    else:
                        extracted[prop_name] = None
                elif prop_type == "checkbox":
                    extracted[prop_name] = prop_data.get("checkbox", False)
                elif prop_type == "url":
                    extracted[prop_name] = prop_data.get("url")
                elif prop_type == "email":
                    extracted[prop_name] = prop_data.get("email")
                elif prop_type == "phone_number":
                    extracted[prop_name] = prop_data.get("phone_number")
                elif prop_type == "relation":
                    relation_data = prop_data.get("relation", [])
                    extracted[prop_name] = [item.get("id") for item in relation_data]
                elif prop_type == "people":
                    people_data = prop_data.get("people", [])
                    extracted[prop_name] = [person.get("id") for person in people_data]
                elif prop_type == "files":
                    files_data = prop_data.get("files", [])
                    extracted[prop_name] = [
                        {
                            "name": file.get("name"),
                            "url": file.get("file", {}).get("url") if file.get("type") == "file" 
                                   else file.get("external", {}).get("url")
                        }
                        for file in files_data
                    ]
                elif prop_type == "created_time":
                    extracted[prop_name] = prop_data.get("created_time")
                elif prop_type == "last_edited_time":
                    extracted[prop_name] = prop_data.get("last_edited_time")
                elif prop_type == "created_by":
                    created_by = prop_data.get("created_by", {})
                    extracted[prop_name] = created_by.get("id")
                elif prop_type == "last_edited_by":
                    edited_by = prop_data.get("last_edited_by", {})
                    extracted[prop_name] = edited_by.get("id")
                else:
                    # For unknown types, store the raw data
                    extracted[prop_name] = prop_data
                    
            except Exception as e:
                logger.warning(f"Error extracting property {prop_name}: {str(e)}")
                extracted[prop_name] = None
        
        return extracted
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array"""
        if not rich_text_array:
            return ""
        
        return "".join([
            text_obj.get("plain_text", "") 
            for text_obj in rich_text_array
        ])
    
    def extract_block_content(self, block: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and simplify block content for easier consumption"""
        block_type = block.get("type")
        content = {
            "id": block.get("id"),
            "type": block_type,
            "created_time": block.get("created_time"),
            "last_edited_time": block.get("last_edited_time"),
            "has_children": block.get("has_children", False)
        }
        
        if block_type == "paragraph":
            content["text"] = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
        elif block_type == "heading_1":
            content["text"] = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
        elif block_type == "heading_2":
            content["text"] = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
        elif block_type == "heading_3":
            content["text"] = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
        elif block_type == "bulleted_list_item":
            content["text"] = self._extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
        elif block_type == "numbered_list_item":
            content["text"] = self._extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
        elif block_type == "to_do":
            to_do_data = block.get("to_do", {})
            content["text"] = self._extract_rich_text(to_do_data.get("rich_text", []))
            content["checked"] = to_do_data.get("checked", False)
        elif block_type == "toggle":
            toggle_data = block.get("toggle", {})
            content["text"] = self._extract_rich_text(toggle_data.get("rich_text", []))
        elif block_type == "quote":
            content["text"] = self._extract_rich_text(block.get("quote", {}).get("rich_text", []))
        elif block_type == "code":
            code_data = block.get("code", {})
            content["text"] = self._extract_rich_text(code_data.get("rich_text", []))
            content["language"] = code_data.get("language")
        elif block_type == "callout":
            callout_data = block.get("callout", {})
            content["text"] = self._extract_rich_text(callout_data.get("rich_text", []))
            content["icon"] = callout_data.get("icon", {})
        elif block_type == "image":
            image_data = block.get("image", {})
            content["type"] = "image"
            content["image_url"] = image_data.get("file", {}).get("url") or image_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(image_data.get("caption", []))
        elif block_type == "video":
            video_data = block.get("video", {})
            content["type"] = "video"
            content["video_url"] = video_data.get("file", {}).get("url") or video_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(video_data.get("caption", []))
        elif block_type == "file":
            file_data = block.get("file", {})
            content["type"] = "file"
            content["file_url"] = file_data.get("file", {}).get("url") or file_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(file_data.get("caption", []))
        elif block_type == "embed":
            embed_data = block.get("embed", {})
            content["type"] = "embed"
            content["embed_url"] = embed_data.get("url")
            content["caption"] = self._extract_rich_text(embed_data.get("caption", []))
        elif block_type == "bookmark":
            bookmark_data = block.get("bookmark", {})
            content["type"] = "bookmark"
            content["bookmark_url"] = bookmark_data.get("url")
            content["caption"] = self._extract_rich_text(bookmark_data.get("caption", []))
        elif block_type == "link_preview":
            link_preview_data = block.get("link_preview", {})
            content["type"] = "link_preview"
            content["link_preview_url"] = link_preview_data.get("url")
            content["caption"] = self._extract_rich_text(link_preview_data.get("caption", []))
        elif block_type == "table":
            table_data = block.get("table", {})
            content["type"] = "table"
            content["table"] = {
                "table_width": table_data.get("table_width"),
                "has_column_header": table_data.get("has_column_header", False),
                "has_row_header": table_data.get("has_row_header", False)
            }
        elif block_type == "table_row":
            table_row_data = block.get("table_row", {})
            content["type"] = "table_row"
            content["cells"] = table_row_data.get("cells", [])
        elif block_type == "divider":
            content["type"] = "divider"
        elif block_type == "breadcrumb":
            content["type"] = "breadcrumb"
        elif block_type == "synced_block":
            synced_block_data = block.get("synced_block", {})
            content["type"] = "synced_block"
            content["synced_from"] = synced_block_data.get("synced_from", {}).get("id")
        elif block_type == "column":
            column_data = block.get("column", {})
            content["type"] = "column"
            content["width"] = column_data.get("width")
        elif block_type == "column_list":
            column_list_data = block.get("column_list", {})
            content["type"] = "column_list"
            content["children"] = [self.extract_block_content(child) for child in column_list_data.get("children", [])]
        elif block_type == "link_to_page":
            link_to_page_data = block.get("link_to_page", {})
            content["type"] = "link_to_page"
            content["page_id"] = link_to_page_data.get("page_id")
        elif block_type == "table_of_contents":
            content["type"] = "table_of_contents"
    
        return content
    def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Get simplified database schema"""
        try:
            database = self.client.databases.retrieve(database_id=database_id)
            properties = database.get("properties", {})
            
            schema = {}
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get("type")
                schema[prop_name] = {
                    "type": prop_type,
                    "id": prop_data.get("id")
                }
                
                # Add additional info for specific types
                if prop_type == "select":
                    options = prop_data.get("select", {}).get("options", [])
                    schema[prop_name]["options"] = [opt.get("name") for opt in options]
                elif prop_type == "multi_select":
                    options = prop_data.get("multi_select", {}).get("options", [])
                    schema[prop_name]["options"] = [opt.get("name") for opt in options]
                elif prop_type == "number":
                    number_format = prop_data.get("number", {}).get("format")
                    schema[prop_name]["format"] = number_format
            
            return {
                "title": database.get("title", [{}])[0].get("plain_text", ""),
                "properties": schema,
                "created_time": database.get("created_time"),
                "last_edited_time": database.get("last_edited_time")
            }
            
        except Exception as e:
            logger.error(f"Error getting database schema: {str(e)}")
            raise
    
    def build_filter(self, property_name: str, filter_type: str, value: Any) -> Dict[str, Any]:
        """Build a filter object for database queries"""
        filter_map = {
            # Text filters
            "equals": {"equals": value},
            "does_not_equal": {"does_not_equal": value},
            "contains": {"contains": value},
            "does_not_contain": {"does_not_contain": value},
            "starts_with": {"starts_with": value},
            "ends_with": {"ends_with": value},
            "is_empty": {"is_empty": True},
            "is_not_empty": {"is_not_empty": True},
            
            # Number filters
            "greater_than": {"greater_than": value},
            "less_than": {"less_than": value},
            "greater_than_or_equal_to": {"greater_than_or_equal_to": value},
            "less_than_or_equal_to": {"less_than_or_equal_to": value},
            
            # Date filters
            "before": {"before": value},
            "after": {"after": value},
            "on_or_before": {"on_or_before": value},
            "on_or_after": {"on_or_after": value},
            
            # Checkbox filters
            "checkbox_equals": {"equals": value}
        }
        
        if filter_type not in filter_map:
            raise ValueError(f"Unsupported filter type: {filter_type}")
        
        return {
            "property": property_name,
            filter_type.split("_")[0]: filter_map[filter_type]
        }
    
    def build_sort(self, property_name: str, direction: str = "ascending") -> Dict[str, Any]:
        """Build a sort object for database queries"""
        if direction not in ["ascending", "descending"]:
            raise ValueError("Direction must be 'ascending' or 'descending'")
        
        return {
            "property": property_name,
            "direction": direction
        }