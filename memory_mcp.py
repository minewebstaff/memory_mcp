import asyncio
import json
import os
import uuid
from datetime import datetime

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Memory Service")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(SCRIPT_DIR, "memory_data.json")
LOG_FILE = os.path.join(SCRIPT_DIR, "memory_operations.log")

memory_store = {}

def load_memory_from_file():
    """Load memory data from JSON file"""
    global memory_store
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                memory_store = json.load(f)
            print(f"Loaded {len(memory_store)} memory entries.")
        else:
            memory_store = {}
            print("Created new memory store.")
    except Exception as e:
        print("Failed to load memory file.")
        memory_store = {}

def save_memory_to_file():
    """Save memory data to JSON file"""
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(memory_store, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        print("Failed to save memory file.")
        return False

def generate_auto_key():
    """Generate auto key from current time"""
    now = datetime.now()
    return f"memory_{now.strftime('%Y%m%d%H%M%S')}"

def create_memory_entry(content: str):
    """Create memory entry with metadata"""
    now = datetime.now().isoformat()
    return {
        "content": content,
        "created_at": now,
        "updated_at": now
    }

def log_operation(operation: str, key: str = None, before: dict = None, after: dict = None, 
                 success: bool = True, error: str = None, metadata: dict = None):
    """Log memory operations to jsonl file"""
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation_id": str(uuid.uuid4()),
            "operation": operation,
            "key": key,
            "before": before,
            "after": after,
            "success": success,
            "error": error,
            "metadata": metadata or {}
        }
        
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception as e:
        print(f"Failed to write log: {str(e)}")

@mcp.tool()
async def list_memory() -> str:
    """
    This tool should be used first whenever the user is asking something related to themselves. 
    List all user info. 
    """
    try:
        log_operation("list", metadata={"entry_count": len(memory_store)})
        
        if memory_store:
            keys = list(memory_store.keys())
            sorted_keys = sorted(keys, key=lambda k: memory_store[k]['created_at'], reverse=True)
            result = f"🧠 {len(keys)} memory entries:\n\n"
            for i, key in enumerate(sorted_keys, 1):
                entry = memory_store[key]
                created_date = entry['created_at'][:10]
                created_time = entry['created_at'][11:19]
                result += f"{i}. [{key}]\n"
                result += f"   {entry['content']}\n"
                result += f"   {created_date} {created_time} ({len(entry['content'])} chars)\n\n"
            return result.rstrip()
        else:
            return "No user info saved yet."
    except Exception as e:
        log_operation("list", success=False, error=str(e))
        return f"Failed to list memory: {str(e)}"

@mcp.tool()
async def create_memory(content: str) -> str:
    """
    Create new memory with important user info (preferences, interests, personal details, current status, etc.) found in conversation. Use even if the user does not explicitly request saving.
    If you find the memory is time sensitive, add time span into it.
    
    Examples to save:
    - Preferences: food, music, hobbies, brands
    - Interests: learning topics, concerns
    - Personal info: job, expertise, location, family
    - Current status: projects, goals, recent events
    - Personality/values: thinking style, priorities
    - Habits/lifestyle: routines

    CRITICAL: When save memories, ALWAYS add [[...]] to any people, concepts, technical terms, etc.
    This enables automatic linking and knowledge graph visualization in Obsidian.
    - People: [[Claude]], [[John Smith]]
    - Technologies: [[Python]], [[AWS]], [[MCP]], [[Jupyter]]
    - Concepts: [[machine learning]], [[data science]]
    - Tools: [[VS Code]], [[Obsidian]]
    - Companies: [[Anthropic]], [[OpenAI]]

    Format: "User is [specific info]" (e.g. "User likes [[strawberry]]", "User is learning [[Python]]", "User interested in [[AI]] in July 2025")

    Args:
        content: User info in "User is..." format.
    """
    try:
        key = generate_auto_key()
        original_key = key
        counter = 1
        while key in memory_store:
            key = f"{original_key}_{counter:02d}"
            counter += 1
        
        new_entry = create_memory_entry(content)
        memory_store[key] = new_entry
        
        log_operation("create", key=key, after=new_entry, 
                     metadata={"content_length": len(content), "auto_generated_key": key})
        
        if save_memory_to_file():
            return f"Saved: '{key}'"
        else:
            return "Saved in memory, file write failed."
    except Exception as e:
        log_operation("create", success=False, error=str(e), 
                     metadata={"attempted_content_length": len(content) if content else 0})
        return f"Failed to save: {str(e)}"

@mcp.tool()
async def update_memory(key: str, content: str) -> str:
    """
    Update existing memory content while preserving the original timestamp.
    Useful for consolidating or refining existing memories without losing temporal information.

    Args:
        key: Memory key to update (e.g., "memory_20250724225317")
        content: New content to replace the existing content
    """
    try:
        if key not in memory_store:
            log_operation("update", key=key, success=False, error="Key not found")
            available_keys = list(memory_store.keys())
            if available_keys:
                return f"Key '{key}' not found. Available: {', '.join(available_keys)}"
            else:
                return f"Key '{key}' not found. No memory data exists."
        
        existing_entry = memory_store[key].copy()  # Make a copy for before state
        now = datetime.now().isoformat()
        
        updated_entry = {
            "content": content,
            "created_at": existing_entry["created_at"],  # Preserve original timestamp
            "updated_at": now
        }
        
        memory_store[key] = updated_entry
        
        log_operation("update", key=key, before=existing_entry, after=updated_entry,
                     metadata={
                         "old_content_length": len(existing_entry["content"]),
                         "new_content_length": len(content),
                         "content_changed": existing_entry["content"] != content
                     })
        
        if save_memory_to_file():
            return f"Updated: '{key}'"
        else:
            return "Updated in memory, file write failed."
    except Exception as e:
        log_operation("update", key=key, success=False, error=str(e),
                     metadata={"attempted_content_length": len(content) if content else 0})
        return f"Failed to update memory: {str(e)}"

@mcp.tool()
async def read_memory(key: str) -> str:
    """
    Read user info by key.
    Args:
        key: Memory key (memory_YYYYMMDDHHMMSS)
    """
    try:
        if key in memory_store:
            entry = memory_store[key]
            log_operation("read", key=key, metadata={"content_length": len(entry["content"])})
            return f"""Key: '{key}'
{entry['content']}
--- Metadata ---
Created: {entry['created_at']}
Updated: {entry['updated_at']}
Chars: {len(entry['content'])}"""
        else:
            log_operation("read", key=key, success=False, error="Key not found")
            available_keys = list(memory_store.keys())
            if available_keys:
                return f"Key '{key}' not found. Available: {', '.join(available_keys)}"
            else:
                return f"Key '{key}' not found. No memory data."
    except Exception as e:
        log_operation("read", key=key, success=False, error=str(e))
        return f"Failed to read memory: {str(e)}"

@mcp.tool()
async def delete_memory(key: str) -> str:
    """
    Delete user info by key.
    Args:
        key: Memory key (memory_YYYYMMDDHHMMSS)
    """
    try:
        if key in memory_store:
            deleted_entry = memory_store[key].copy()  # Capture before deletion
            del memory_store[key]
            
            log_operation("delete", key=key, before=deleted_entry,
                         metadata={"deleted_content_length": len(deleted_entry["content"])})
            
            if save_memory_to_file():
                return f"Deleted '{key}'"
            else:
                return f"Deleted '{key}', file write failed."
        else:
            log_operation("delete", key=key, success=False, error="Key not found")
            available_keys = list(memory_store.keys())
            if available_keys:
                return f"Key '{key}' not found. Available: {', '.join(available_keys)}"
            else:
                return f"Key '{key}' not found. No memory data."
    except Exception as e:
        log_operation("delete", key=key, success=False, error=str(e))
        return f"Failed to delete memory: {str(e)}"

@mcp.resource("memory://info")
def get_memory_info() -> str:
    """Provide memory service info"""
    total_chars = sum(len(entry['content']) for entry in memory_store.values())
    return (
        f"User Memory System Info:\n"
        f"- Entries: {len(memory_store)}\n"
        f"- Total chars: {total_chars}\n"
        f"- Data file: {MEMORY_FILE}\n"
        f"- Tools: save_memory, read_memory, list_memory, delete_memory\n"
        f"- Key format: memory_YYYYMMDDHHMMSS\n"
        f"- Save format: 'User is ...'\n"
    )

if __name__ == "__main__":
    print(os.getcwd())
    load_memory_from_file()
    mcp.run(transport='stdio')
    