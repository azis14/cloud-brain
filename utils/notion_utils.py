from typing import Dict, List, Any, Optional, Set
from notion_client import Client, AsyncClient
import logging
import asyncio

logger = logging.getLogger(__name__)

class NotionUtils:
    """Utility class for common Notion operations with enhanced data extraction for RAG"""
    
    def __init__(self, client: Client | AsyncClient):
        self.client = client
        self._is_async = isinstance(client, AsyncClient)
        # Cache for fetched child pages to avoid redundant API calls
        self._page_cache: Dict[str, Dict[str, Any]] = {}
        # Track synced block IDs to avoid duplicates
        self._synced_block_ids: Set[str] = set()
    
    # ==================== Page Property Extraction ====================
    
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
                    extracted[prop_name] = [
                        person.get("name") or person.get("id") 
                        for person in people_data
                    ]
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
                    extracted[prop_name] = created_by.get("name") or created_by.get("id")
                elif prop_type == "last_edited_by":
                    edited_by = prop_data.get("last_edited_by", {})
                    edited_by_name = edited_by.get("name") or edited_by.get("id")
                    extracted[prop_name] = edited_by_name
                elif prop_type == "formula":
                    formula_data = prop_data.get("formula", {})
                    extracted[prop_name] = formula_data.get("string") or formula_data.get("number")
                elif prop_type == "rollup":
                    rollup_data = prop_data.get("rollup", {})
                    rollup_type = rollup_data.get("type")
                    if rollup_type == "array":
                        extracted[prop_name] = rollup_data.get("array", [])
                    elif rollup_type == "number":
                        extracted[prop_name] = rollup_data.get("number")
                    elif rollup_type == "string":
                        extracted[prop_name] = rollup_data.get("string")
                else:
                    # For unknown types, store the raw data
                    extracted[prop_name] = prop_data
                    
            except Exception as e:
                logger.warning(f"Error extracting property {prop_name}: {str(e)}")
                extracted[prop_name] = None
        
        return extracted
    
    def _extract_rich_text(self, rich_text_array: List[Dict[str, Any]]) -> str:
        """Extract plain text from rich text array with mention handling"""
        if not rich_text_array:
            return ""
        
        text_parts = []
        for text_obj in rich_text_array:
            text_type = text_obj.get("type", "text")
            
            if text_type == "text":
                text_parts.append(text_obj.get("plain_text", ""))
            elif text_type == "mention":
                mention_data = text_obj.get("mention", {})
                mention_type = mention_data.get("type")
                
                if mention_type == "user":
                    user = mention_data.get("user", {})
                    text_parts.append(f"@{user.get('name', 'Unknown User')}")
                elif mention_type == "page":
                    page_id = mention_data.get("page", {}).get("id")
                    text_parts.append(f"[Page: {page_id}]")
                elif mention_type == "database":
                    db_id = mention_data.get("database", {}).get("id")
                    text_parts.append(f"[Database: {db_id}]")
                elif mention_type == "date":
                    date_info = mention_data.get("date", {})
                    text_parts.append(f"[Date: {date_info.get('start', 'Unknown')}]")
                elif mention_type == "link_preview":
                    url = mention_data.get("url", "")
                    text_parts.append(f"[Link: {url}]")
                else:
                    text_parts.append(text_obj.get("plain_text", ""))
            else:
                text_parts.append(text_obj.get("plain_text", ""))
        
        return "".join(text_parts)
    
    # ==================== Block Content Extraction ====================
    
    def extract_block_content(self, block: Dict[str, Any], depth: int = 0) -> Dict[str, Any]:
        """Extract and simplify block content for easier consumption with recursive children"""
        block_type = block.get("type")
        block_id = block.get("id")
        
        # Skip duplicate synced blocks
        if block_type == "synced_block":
            synced_from_id = block.get("synced_block", {}).get("synced_from", {}).get("id")
            if synced_from_id in self._synced_block_ids:
                return {"id": block_id, "type": "synced_block", "skipped": True, "reason": "duplicate"}
            self._synced_block_ids.add(synced_from_id)
        
        content = {
            "id": block_id,
            "type": block_type,
            "created_time": block.get("created_time"),
            "last_edited_time": block.get("last_edited_time"),
            "has_children": block.get("has_children", False),
            "depth": depth
        }
        
        # Extract text content based on block type
        if block_type == "paragraph":
            content["text"] = self._extract_rich_text(block.get("paragraph", {}).get("rich_text", []))
        elif block_type == "heading_1":
            content["text"] = self._extract_rich_text(block.get("heading_1", {}).get("rich_text", []))
            content["level"] = 1
        elif block_type == "heading_2":
            content["text"] = self._extract_rich_text(block.get("heading_2", {}).get("rich_text", []))
            content["level"] = 2
        elif block_type == "heading_3":
            content["text"] = self._extract_rich_text(block.get("heading_3", {}).get("rich_text", []))
            content["level"] = 3
        elif block_type == "bulleted_list_item":
            content["text"] = self._extract_rich_text(block.get("bulleted_list_item", {}).get("rich_text", []))
            content["list_type"] = "bullet"
        elif block_type == "numbered_list_item":
            content["text"] = self._extract_rich_text(block.get("numbered_list_item", {}).get("rich_text", []))
            content["list_type"] = "number"
        elif block_type == "to_do":
            to_do_data = block.get("to_do", {})
            content["text"] = self._extract_rich_text(to_do_data.get("rich_text", []))
            content["checked"] = to_do_data.get("checked", False)
        elif block_type == "toggle":
            toggle_data = block.get("toggle", {})
            content["text"] = self._extract_rich_text(toggle_data.get("rich_text", []))
            content["is_toggle"] = True
        elif block_type == "quote":
            content["text"] = self._extract_rich_text(block.get("quote", {}).get("rich_text", []))
            content["is_quote"] = True
        elif block_type == "callout":
            callout_data = block.get("callout", {})
            content["text"] = self._extract_rich_text(callout_data.get("rich_text", []))
            content["icon"] = callout_data.get("icon", {})
            content["is_callout"] = True
        elif block_type == "code":
            code_data = block.get("code", {})
            content["text"] = self._extract_rich_text(code_data.get("rich_text", []))
            content["language"] = code_data.get("language", "plain text")
            content["is_code"] = True
        elif block_type == "equation":
            equation_data = block.get("equation", {})
            content["expression"] = equation_data.get("expression", "")
            content["is_equation"] = True
        elif block_type == "divider":
            content["is_divider"] = True
        elif block_type == "breadcrumb":
            content["is_breadcrumb"] = True
        elif block_type == "table_of_contents":
            content["is_toc"] = True
        elif block_type == "link_to_page":
            link_to_page_data = block.get("link_to_page", {})
            content["page_id"] = link_to_page_data.get("page_id")
            content["database_id"] = link_to_page_data.get("database_id")
            content["is_link"] = True
        elif block_type == "bookmark":
            bookmark_data = block.get("bookmark", {})
            content["url"] = bookmark_data.get("url")
            content["caption"] = self._extract_rich_text(bookmark_data.get("caption", []))
        elif block_type == "embed":
            embed_data = block.get("embed", {})
            content["url"] = embed_data.get("url")
            content["caption"] = self._extract_rich_text(embed_data.get("caption", []))
        elif block_type == "image":
            image_data = block.get("image", {})
            content["url"] = image_data.get("file", {}).get("url") or image_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(image_data.get("caption", []))
            content["type_detail"] = "image"
        elif block_type == "video":
            video_data = block.get("video", {})
            content["url"] = video_data.get("file", {}).get("url") or video_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(video_data.get("caption", []))
            content["type_detail"] = "video"
        elif block_type == "file":
            file_data = block.get("file", {})
            content["url"] = file_data.get("file", {}).get("url") or file_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(file_data.get("caption", []))
            content["type_detail"] = "file"
        elif block_type == "pdf":
            pdf_data = block.get("pdf", {})
            content["url"] = pdf_data.get("file", {}).get("url") or pdf_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(pdf_data.get("caption", []))
            content["type_detail"] = "pdf"
        elif block_type == "audio":
            audio_data = block.get("audio", {})
            content["url"] = audio_data.get("file", {}).get("url") or audio_data.get("external", {}).get("url")
            content["caption"] = self._extract_rich_text(audio_data.get("caption", []))
            content["type_detail"] = "audio"
        elif block_type == "link_preview":
            link_preview_data = block.get("link_preview", {})
            content["url"] = link_preview_data.get("url")
            content["type_detail"] = "link_preview"
        elif block_type == "child_page":
            child_page_data = block.get("child_page", {})
            content["title"] = child_page_data.get("title", "")
            content["child_page_id"] = block_id  # The block ID is the child page ID
            content["type_detail"] = "child_page"
        elif block_type == "child_database":
            child_db_data = block.get("child_database", {})
            content["title"] = child_db_data.get("title", "")
            content["child_database_id"] = block_id
            content["type_detail"] = "child_database"
        elif block_type == "table":
            table_data = block.get("table", {})
            content["table_width"] = table_data.get("table_width", 0)
            content["has_column_header"] = table_data.get("has_column_header", False)
            content["has_row_header"] = table_data.get("has_row_header", False)
            content["type_detail"] = "table"
        elif block_type == "table_row":
            table_row_data = block.get("table_row", {})
            cells = table_row_data.get("cells", [])
            # Convert cell rich_text to plain text
            content["cells"] = [self._extract_rich_text(cell) for cell in cells]
            content["type_detail"] = "table_row"
        elif block_type == "column_list":
            content["type_detail"] = "column_list"
        elif block_type == "column":
            column_data = block.get("column", {})
            content["width"] = column_data.get("width")
            content["type_detail"] = "column"
        elif block_type == "synced_block":
            synced_block_data = block.get("synced_block", {})
            content["synced_from_id"] = synced_block_data.get("synced_from", {}).get("id")
            content["type_detail"] = "synced_block"
        elif block_type == "template":
            template_data = block.get("template", {})
            content["text"] = self._extract_rich_text(template_data.get("rich_text", []))
            content["type_detail"] = "template"
        else:
            content["unknown_type"] = True
            logger.debug(f"Unknown block type: {block_type}")
        
        return content
    
    # ==================== Recursive Block Fetching ====================
    
    async def fetch_all_blocks_recursive(
        self, 
        page_id: str, 
        max_depth: int = 10,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch all blocks from a page recursively, including nested children.
        
        Args:
            page_id: The ID of the page to fetch blocks from
            max_depth: Maximum recursion depth to prevent infinite loops
            page_size: Number of blocks to fetch per API call
        
        Returns:
            List of all blocks with their children nested
        """
        self._synced_block_ids = set()  # Reset synced block tracking
        return await self._fetch_blocks_recursive(
            block_id=page_id,
            current_depth=0,
            max_depth=max_depth,
            page_size=page_size
        )
    
    async def _fetch_blocks_recursive(
        self,
        block_id: str,
        current_depth: int,
        max_depth: int,
        page_size: int
    ) -> List[Dict[str, Any]]:
        """Internal recursive method to fetch blocks"""
        if current_depth > max_depth:
            logger.warning(f"Max depth {max_depth} reached for block {block_id}")
            return []
        
        all_blocks = []
        has_more = True
        next_cursor = None
        
        while has_more:
            try:
                # Fetch blocks with pagination
                kwargs = {
                    "block_id": block_id,
                    "page_size": page_size
                }
                if next_cursor:
                    kwargs["start_cursor"] = next_cursor
                
                response = await self.client.blocks.children.list(**kwargs)
                blocks = response.get("results", [])
                has_more = response.get("has_more", False)
                next_cursor = response.get("next_cursor")
                
                # Process each block
                for block in blocks:
                    # Extract block content
                    extracted_block = self.extract_block_content(block, depth=current_depth)
                    
                    # Recursively fetch children if present
                    if block.get("has_children", False) and current_depth < max_depth:
                        children = await self._fetch_blocks_recursive(
                            block_id=block["id"],
                            current_depth=current_depth + 1,
                            max_depth=max_depth,
                            page_size=page_size
                        )
                        extracted_block["children"] = children
                    
                    all_blocks.append(extracted_block)
                    
            except Exception as e:
                logger.error(f"Error fetching blocks for {block_id} at depth {current_depth}: {str(e)}")
                break
        
        return all_blocks
    
    # ==================== Child Page Resolution ====================
    
    async def fetch_child_page_content(self, page_id: str) -> Dict[str, Any]:
        """
        Fetch content of a child page for inlining into parent content.
        
        Args:
            page_id: The ID of the child page to fetch
        
        Returns:
            Dictionary with page data and blocks
        """
        # Check cache first
        if page_id in self._page_cache:
            logger.debug(f"Using cached content for page {page_id}")
            return self._page_cache[page_id]
        
        try:
            # Fetch page properties
            page = await self.client.pages.retrieve(page_id=page_id)
            
            # Fetch page blocks
            blocks = await self.fetch_all_blocks_recursive(page_id, max_depth=5)
            
            page_data = {
                "id": page_id,
                "properties": self.extract_page_properties(page),
                "blocks": blocks,
                "url": page.get("url"),
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time")
            }
            
            # Cache the result
            self._page_cache[page_id] = page_data
            
            return page_data
            
        except Exception as e:
            logger.error(f"Error fetching child page {page_id}: {str(e)}")
            return {"id": page_id, "error": str(e)}
    
    async def resolve_linked_pages(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Resolve link_to_page blocks by fetching their content.
        
        Args:
            blocks: List of extracted blocks
        
        Returns:
            Blocks with linked page content inlined
        """
        for block in blocks:
            if block.get("type") == "link_to_page":
                page_id = block.get("page_id")
                if page_id:
                    child_content = await self.fetch_child_page_content(page_id)
                    block["resolved_content"] = child_content
            
            # Recursively resolve children
            if "children" in block:
                await self.resolve_linked_pages(block["children"])
        
        return blocks
    
    # ==================== Clean Text Generation ====================
    
    def blocks_to_markdown(
        self, 
        blocks: List[Dict[str, Any]], 
        page_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> str:
        """
        Convert extracted blocks to clean markdown text for RAG.
        
        Args:
            blocks: List of extracted blocks
            page_metadata: Optional page metadata to include
            include_metadata: Whether to include metadata in output
        
        Returns:
            Clean markdown-formatted text
        """
        markdown_parts = []
        
        # Add page metadata as header
        if include_metadata and page_metadata:
            markdown_parts.append(self._format_page_metadata(page_metadata))
        
        # Process blocks
        markdown_parts.append(self._blocks_to_markdown_recursive(blocks))
        
        return "\n\n".join(markdown_parts)
    
    def _format_page_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format page metadata as markdown header"""
        parts = []
        
        # Title
        title = metadata.get("title", "")
        if title:
            parts.append(f"# {title}")
        
        # Properties
        properties = metadata.get("properties", {})
        if properties:
            parts.append("## Page Properties\n")
            for prop_name, prop_value in properties.items():
                if prop_value is not None:
                    if isinstance(prop_value, list):
                        prop_value = ", ".join(str(v) for v in prop_value)
                    parts.append(f"- **{prop_name}**: {prop_value}")
        
        # URL
        url = metadata.get("url")
        if url:
            parts.append(f"\nSource: {url}")
        
        return "\n".join(parts)
    
    def _blocks_to_markdown_recursive(
        self, 
        blocks: List[Dict[str, Any]], 
        indent_level: int = 0
    ) -> str:
        """Recursively convert blocks to markdown"""
        markdown_parts = []
        list_counter = 1
        
        for block in blocks:
            # Skip duplicate synced blocks and empty blocks
            if block.get("skipped") or block.get("is_divider") and not markdown_parts:
                continue
            
            block_type = block.get("type", "")
            text = block.get("text", "")
            indent = "  " * indent_level
            
            # Handle different block types
            if block_type in ["heading_1", "heading_2", "heading_3"]:
                level = block.get("level", 1)
                markdown_parts.append(f"{'#' * level} {text}")
            
            elif block_type == "paragraph":
                if text:
                    markdown_parts.append(f"{indent}{text}")
            
            elif block_type == "bulleted_list_item":
                markdown_parts.append(f"{indent}- {text}")
            
            elif block_type == "numbered_list_item":
                markdown_parts.append(f"{indent}{list_counter}. {text}")
                list_counter += 1
            
            elif block_type == "to_do":
                checked = block.get("checked", False)
                checkbox = "[x]" if checked else "[ ]"
                markdown_parts.append(f"{indent}- {checkbox} {text}")
            
            elif block_type == "toggle":
                markdown_parts.append(f"{indent}<details><summary>{text}</summary>")
                if "children" in block:
                    markdown_parts.append(self._blocks_to_markdown_recursive(
                        block["children"], indent_level + 1
                    ))
                markdown_parts.append(f"{indent}</details>")
            
            elif block_type == "quote":
                lines = text.split("\n")
                quoted = "\n".join(f"{indent}> {line}" for line in lines)
                markdown_parts.append(quoted)
            
            elif block_type == "callout":
                icon = block.get("icon", {})
                icon_str = ""
                if icon:
                    icon_type = icon.get("type")
                    if icon_type == "emoji":
                        icon_str = icon.get("emoji", "")
                markdown_parts.append(f"{indent}{icon_str} **{text}**")
            
            elif block_type == "code":
                language = block.get("language", "plain text")
                markdown_parts.append(f"{indent}```{language}\n{text}\n{indent}```")
            
            elif block_type == "equation":
                expression = block.get("expression", "")
                markdown_parts.append(f"{indent}$$ {expression} $$")
            
            elif block_type == "table":
                markdown_parts.append(self._format_table_markdown(block, blocks))
            
            elif block_type == "column_list":
                # Process columns inline
                if "children" in block:
                    markdown_parts.append(self._blocks_to_markdown_recursive(
                        block["children"], indent_level
                    ))
            
            elif block_type == "child_page":
                title = block.get("title", "Untitled")
                child_id = block.get("child_page_id")
                markdown_parts.append(f"{indent}### 📄 Child Page: {title}")
                if "resolved_content" in block:
                    markdown_parts.append(self._blocks_to_markdown_recursive(
                        block["resolved_content"].get("blocks", []), indent_level
                    ))
            
            elif block_type == "link_to_page":
                page_id = block.get("page_id")
                if "resolved_content" in block:
                    resolved = block["resolved_content"]
                    title = resolved.get("properties", {}).get("title", "Linked Page")
                    markdown_parts.append(f"{indent}### 🔗 Linked: {title}")
                    markdown_parts.append(self._blocks_to_markdown_recursive(
                        resolved.get("blocks", []), indent_level
                    ))
            
            elif block_type in ["image", "video", "file", "pdf", "audio"]:
                url = block.get("url", "")
                caption = block.get("caption", "")
                type_name = block.get("type_detail", block_type)
                markdown_parts.append(f"{indent}*[{type_name}: {url}]*")
                if caption:
                    markdown_parts.append(f"{indent}*Caption: {caption}*")
            
            elif block_type == "bookmark":
                url = block.get("url", "")
                caption = block.get("caption", "")
                markdown_parts.append(f"{indent}🔖 [{url}]({url})")
                if caption:
                    markdown_parts.append(f"{indent}*{caption}*")
            
            elif block_type == "embed":
                url = block.get("url", "")
                caption = block.get("caption", "")
                markdown_parts.append(f"{indent}*[Embed: {url}]*")
                if caption:
                    markdown_parts.append(f"{indent}*{caption}*")
            
            elif block_type == "divider":
                markdown_parts.append("---")
            
            elif block_type == "table_of_contents":
                markdown_parts.append(f"{indent}*[Table of Contents]*")
            
            elif block_type == "breadcrumb":
                pass  # Skip breadcrumb in markdown output
            
            elif block_type == "synced_block":
                if block.get("skipped"):
                    continue
                if "children" in block:
                    markdown_parts.append(self._blocks_to_markdown_recursive(
                        block["children"], indent_level
                    ))
            
            elif block_type == "template":
                markdown_parts.append(f"{indent}*[Template: {text}]*")
            
            else:
                # Unknown block type - include text if available
                if text:
                    markdown_parts.append(f"{indent}{text}")
        
        return "\n".join(markdown_parts)
    
    def _format_table_markdown(
        self, 
        table_block: Dict[str, Any], 
        all_blocks: List[Dict[str, Any]]
    ) -> str:
        """Format table block and its rows as markdown table"""
        table_id = table_block.get("id")
        if not table_id:
            return ""
        
        # Find table rows that belong to this table
        # In Notion API, table rows are children of the table block
        rows = table_block.get("children", [])
        
        if not rows:
            return ""
        
        markdown_lines = []
        
        for i, row in enumerate(rows):
            cells = row.get("cells", [])
            if not cells:
                continue
            
            # Format row as markdown table row
            row_text = "| " + " | ".join(str(cell) for cell in cells) + " |"
            markdown_lines.append(row_text)
            
            # Add separator after header row
            if i == 0:
                separator = "| " + " | ".join("---" for _ in cells) + " |"
                markdown_lines.append(separator)
        
        return "\n".join(markdown_lines) if markdown_lines else ""
    
    # ==================== Complete Page Extraction ====================
    
    async def extract_complete_page_data(
        self, 
        page_id: str,
        include_child_pages: bool = True,
        resolve_links: bool = True,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        """
        Extract complete page data including all nested content.
        
        Args:
            page_id: The ID of the page to extract
            include_child_pages: Whether to fetch child page content
            resolve_links: Whether to resolve link_to_page blocks
            max_depth: Maximum recursion depth for nested blocks
        
        Returns:
            Complete page data with properties, blocks, and markdown content
        """
        self._page_cache = {}  # Reset cache for new extraction
        self._synced_block_ids = set()
        
        try:
            # Fetch page properties
            page = await self.client.pages.retrieve(page_id=page_id)
            
            # Fetch all blocks recursively
            blocks = await self.fetch_all_blocks_recursive(page_id, max_depth=max_depth)
            
            # Resolve linked pages if requested
            if resolve_links:
                blocks = await self.resolve_linked_pages(blocks)
            
            # Fetch child pages if requested
            if include_child_pages:
                blocks = await self._fetch_inline_child_pages(blocks)
            
            # Extract properties
            properties = self.extract_page_properties(page)
            
            # Get page title
            title = ""
            for prop_name, prop_value in properties.items():
                if prop_name == "title" or isinstance(prop_value, str):
                    title = prop_value
                    break
            
            # Generate markdown content
            page_metadata = {
                "title": title,
                "properties": properties,
                "url": page.get("url"),
                "id": page_id
            }
            markdown_content = self.blocks_to_markdown(blocks, page_metadata)
            
            return {
                "id": page_id,
                "url": page.get("url"),
                "created_time": page.get("created_time"),
                "last_edited_time": page.get("last_edited_time"),
                "properties": properties,
                "blocks": blocks,
                "markdown_content": markdown_content,
                "child_pages_fetched": len(self._page_cache)
            }
            
        except Exception as e:
            logger.error(f"Error extracting complete page data for {page_id}: {str(e)}")
            raise
    
    async def _fetch_inline_child_pages(
        self, 
        blocks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Fetch and inline child page content"""
        for block in blocks:
            if block.get("type") == "child_page":
                child_id = block.get("child_page_id")
                if child_id:
                    child_content = await self.fetch_child_page_content(child_id)
                    block["resolved_content"] = child_content
            
            # Recursively process children
            if "children" in block:
                await self._fetch_inline_child_pages(block["children"])
        
        return blocks
    
    # ==================== Database Operations ====================
    
    async def get_database_schema(self, database_id: str) -> Dict[str, Any]:
        """Get simplified database schema"""
        try:
            database = await self.client.databases.retrieve(database_id=database_id)
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
                elif prop_type == "relation":
                    schema[prop_name]["relation_database_id"] = prop_data.get("relation", {}).get("database_id")
                elif prop_type == "rollup":
                    schema[prop_name]["rollup_property"] = prop_data.get("rollup", {}).get("function")
            
            # Get database title
            title = ""
            title_array = database.get("title", [])
            if title_array:
                title = self._extract_rich_text(title_array)
            
            return {
                "id": database_id,
                "title": title,
                "properties": schema,
                "created_time": database.get("created_time"),
                "last_edited_time": database.get("last_edited_time"),
                "url": database.get("url")
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
    
    # ==================== Text Extraction for RAG ====================
    
    def extract_text_for_embedding(
        self, 
        page_data: Dict[str, Any],
        include_properties: bool = True,
        include_urls: bool = False
    ) -> str:
        """
        Extract clean text optimized for embedding generation.
        
        Args:
            page_data: Complete page data from extract_complete_page_data
            include_properties: Whether to include page properties
            include_urls: Whether to include URLs in output
        
        Returns:
            Clean text string optimized for embeddings
        """
        text_parts = []
        
        # Add title
        properties = page_data.get("properties", {})
        title = properties.get("title", "")
        if title:
            text_parts.append(f"Title: {title}")
        
        # Add properties
        if include_properties:
            text_parts.append("Properties:")
            for prop_name, prop_value in properties.items():
                if prop_name == "title":
                    continue
                if prop_value is not None:
                    if isinstance(prop_value, list):
                        prop_value = ", ".join(str(v) for v in prop_value)
                    text_parts.append(f"  {prop_name}: {prop_value}")
        
        # Add main content
        markdown_content = page_data.get("markdown_content", "")
        if markdown_content:
            # Remove markdown formatting for cleaner embeddings
            clean_text = self._clean_markdown_for_embedding(markdown_content)
            text_parts.append("Content:")
            text_parts.append(clean_text)
        
        # Add URL if requested
        if include_urls:
            url = page_data.get("url")
            if url:
                text_parts.append(f"Source URL: {url}")
        
        return "\n".join(text_parts)
    
    def _clean_markdown_for_embedding(self, markdown: str) -> str:
        """Clean markdown text for better embedding quality"""
        import re
        
        text = markdown
        
        # Remove code block markers but keep content
        text = re.sub(r'```\w*\n?', '', text)
        text = re.sub(r'```', '', text)
        
        # Remove equation markers
        text = re.sub(r'\$\$\s*', '', text)
        
        # Simplify headers
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
        
        # Remove list markers
        text = re.sub(r'^[\-\*\•]\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\d+\.\s*', '', text, flags=re.MULTILINE)
        
        # Remove checkbox markers
        text = re.sub(r'^\[[ x]\]\s*', '', text, flags=re.MULTILINE)
        
        # Remove quote markers
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # Remove table separators
        text = re.sub(r'^\|[-\s|]+\|$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\|\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*\|$', '', text, flags=re.MULTILINE)
        
        # Remove details/summary tags
        text = re.sub(r'<details>', '', text)
        text = re.sub(r'</details>', '', text)
        text = re.sub(r'<summary>', '', text)
        text = re.sub(r'</summary>', '', text)
        
        # Remove emoji and special characters that don't add semantic value
        text = re.sub(r'📄|🔗|🔖', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        
        return text.strip()
