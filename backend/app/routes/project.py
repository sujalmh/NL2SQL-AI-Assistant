from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
from dotenv import load_dotenv
import os
load_dotenv()

project_bp = Blueprint("project", __name__)

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"] 

projects_collection = db["projects"]


@project_bp.route("/<chat_id>", methods=["GET"])
def get_project_by_chat_id(chat_id):
    # Fetch project info
    project = db.projects.find_one({"chat_id": chat_id})
    if not project:
        return jsonify({"error": "Project not found"}), 404

    # Fetch messages for this chat
    messages_cursor = db.chats.find({"chat_id": chat_id}).sort("timestamp", 1)
    messages = []
    for msg in messages_cursor:
        msg["_id"] = str(msg["_id"])  # Optional: to avoid ObjectId issues on frontend
        messages.append(msg)

    # Prepare schema
    database_details = project.get("database_details", {})
    tables = database_details.get("tables", [])

    return jsonify({
        "chat_id": chat_id,
        "db_name": project.get("name"),
        "original_filename": project.get("original_filename"),
        "schema": tables,
        "database_uploaded": project.get("database_uploaded", False),
        "description": project.get("description"),
        "created_at": project.get("created_at").isoformat(),
        "messages": messages
    })




def serialize_project(project):
    return {
        "id": str(project.get("_id")),
        "name": project.get("name", ""),
        "description": project.get("description", ""),
        "chat_id": project.get("chat_id", ""),
        "original_filename": project.get("original_filename", ""),
        "file_path": project.get("file_path", ""),
        "status": project.get("database_details", {}).get("status", "unknown"),
        "created_at": project.get("created_at", datetime.utcnow()).isoformat(),
        "updated_at": project.get("updated_at", datetime.utcnow()).isoformat(),
        "last_accessed": project.get("last_accessed", datetime.utcnow()).isoformat(),
        "database_uploaded": project.get("database_uploaded", False),
        "shared_with": project.get("shared_with", [])
    }



@project_bp.route("/get_projects", methods=["GET"])
def get_user_projects():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id in query params"}), 400

        # Query projects that belong to this user
        projects = list(projects_collection.find({"user_id": int(user_id)}))
        serialized = [serialize_project(p) for p in projects]
        return jsonify(serialized), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

