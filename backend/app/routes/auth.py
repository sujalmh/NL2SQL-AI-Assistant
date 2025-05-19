from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"]
users_collection = db["users"]

# Secret key for JWT
SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

auth_bp = Blueprint('auth', __name__)


def get_next_user_id():
    counter = db.counters.find_one_and_update(
        {"_id": "user_id"},
        {"$inc": {"user_seq_val": 1}},
        return_document=True
    )
    if counter is None:
        db.counters.insert_one({"_id": "user_id", "user_seq_val": 1})
        return 1
    return counter["user_seq_val"]

# Signup Route
@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    full_name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    
    if not full_name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 409
    
    hashed_password = generate_password_hash(password)
    
    user = {
        "user_id": get_next_user_id(),
        "full_name": full_name,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow()
    }
    
    users_collection.insert_one(user)
    return jsonify({"message": "User registered successfully"}), 201

# Login Route
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    user = users_collection.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    user_id = (user["user_id"])

    token = jwt.encode({
        "user_id": str(user["_id"]),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")
    
    return jsonify({"token": token, "user_id": user_id ,"message": "Login successful", "user_name": user["full_name"], "user_email": user["email"]}), 200