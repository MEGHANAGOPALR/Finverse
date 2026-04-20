from backend.managers.file_manager import read_json, write_json
from datetime import datetime

# --- Chat File Path Management ---
def get_chat_filepath(user_id):
    """Returns the filename for a user's master chat file."""
    return f'{user_id}_chats.json'

def get_user_chats(user_id):
    """Retrieves the entire chat data structure for a user."""
    return read_json(get_chat_filepath(user_id), default={})

def save_user_chats(user_id, chats):
    """Saves the entire chat data structure for a user."""
    write_json(get_chat_filepath(user_id), chats)

# --- Core Chat Operations ---
def get_chat_names(user_id):
    """Returns a list of all chat names (keys)."""
    chats = get_user_chats(user_id)
    # Sort chats by the last message time if available
    sorted_chats = sorted(chats.keys(), key=lambda k: chats[k].get('last_updated', ''), reverse=True)
    return sorted_chats

def get_chat_history(user_id, chat_name):
    """Returns the message list for a specific chat."""
    chats = get_user_chats(user_id)
    return chats.get(chat_name, {}).get('messages', [])

def create_chat(user_id, chat_name):
    """Creates a new chat session."""
    chats = get_user_chats(user_id)
    
    if chat_name in chats:
        return False, f"Chat name '{chat_name}' already exists."

    chats[chat_name] = {
        'messages': [],
        'created_at': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat(),
    }
    save_user_chats(user_id, chats)
    return True, "New chat created."

def rename_chat(user_id, old_name, new_name):
    """Renames an existing chat session."""
    chats = get_user_chats(user_id)
    
    if old_name not in chats:
        return False, "Original chat not found."
    
    if new_name in chats:
        return False, "New chat name already exists."

    # Perform the rename operation
    chats[new_name] = chats.pop(old_name)
    chats[new_name]['last_updated'] = datetime.now().isoformat()
    
    save_user_chats(user_id, chats)
    return True, "Chat renamed successfully."


def add_message(user_id, chat_name, role, content):
    """Adds a new message to the specified chat history."""
    chats = get_user_chats(user_id)
    chat = chats.get(chat_name)

    if not chat:
        # Create chat if it doesn't exist (e.g., first message in a new session)
        create_chat(user_id, chat_name)
        chat = chats.get(chat_name) # Fetch it back after creation
        if not chat: return # Failsafe

    new_message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    
    chat['messages'].append(new_message)
    chat['last_updated'] = datetime.now().isoformat()

    save_user_chats(user_id, chats)