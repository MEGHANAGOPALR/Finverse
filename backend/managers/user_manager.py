# backend/managers/user_manager.py

import uuid
from datetime import datetime # <<< FIX 1: Import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from backend.managers.file_manager import read_json, write_json

USERS_FILE = 'users.json'

def get_users():
    """Reads all user data from the JSON file."""
    return read_json(USERS_FILE, default={})

def get_user_profile(user_id):
    """Retrieves a single user's profile."""
    users = get_users()
    return users.get(user_id)

def create_user(name, email, password):
    """Creates a new user account."""
    users = get_users()
    
    # Check if email already exists
    for user_id, user_data in users.items():
        # Using .get for robustness against inconsistent data
        if user_data.get('email', '').lower() == email.lower(): 
            return False, "This email is already registered.", None

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    
    new_user = {
        'id': user_id,
        'name': name,
        'email': email,
        'password_hash': password_hash,
        'created_at': datetime.now().isoformat(), # <<< FIX 1: 'datetime' is now defined
        'onboarding': {} # Placeholder for financial profile
    }
    
    users[user_id] = new_user
    write_json(USERS_FILE, users)
    
    return True, "User created successfully.", user_id

def authenticate_user(email, password):
    """Authenticates a user by email and password."""
    users = get_users()
    for user_id, user_data in users.items():
        # Using .get for robustness and clean email check
        if user_data.get('email', '').lower() == email.lower(): 
            password_hash = user_data.get('password_hash')
            # <<< FIX 2: Check if password_hash exists before trying to check it
            if password_hash and check_password_hash(password_hash, password): 
                return user_id
    return None

def update_user_profile(user_id, data):
    """Updates basic profile info or nested onboarding data."""
    users = get_users()
    profile = users.get(user_id)
    
    if not profile:
        return False, "User not found."
    
    # 1. Handle basic info update (Name/Email)
    if 'name' in data:
        profile['name'] = data['name']
    if 'email' in data:
        profile['email'] = data['email']
    
    # 2. Handle password update
    if 'password' in data and data['password']:
        profile['password_hash'] = generate_password_hash(data['password'])
        
    # 3. Handle Onboarding data update (sent from onboarding.html POST request)
    if 'onboarding' in data and isinstance(data['onboarding'], dict):
        # Merge new onboarding data with existing data
        profile['onboarding'].update(data['onboarding'])
        
    users[user_id] = profile
    write_json(USERS_FILE, users)
    return True, "Profile updated successfully."