from flask import current_app

def get_users_collection():
    return current_app.db["users"]  # Access "users" collection
