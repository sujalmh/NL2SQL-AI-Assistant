from flask import Blueprint, request, jsonify
import sqlite3
import uuid
from datetime import datetime
from pymongo import MongoClient

chat_bp = Blueprint('chat', __name__)

chat_history = []
file = "shop.db"

from dotenv import load_dotenv
import os
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"] 

def get_database_schema():
    conn = sqlite3.connect(f"input\\{file}")
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    if not tables:
        return []

    schema = []
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [col[1] for col in columns_info]  # col[1] is the column name

        schema.append({
            "table_name": table_name,
            "columns": column_names
        })

    conn.close()
    return schema

def get_sample_data(table_name, limit=5):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
    rows = cursor.fetchall()
    
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()
    
    return {"columns": columns, "data": [dict(zip(columns, row)) for row in rows]}

@chat_bp.route("/chat-history", methods=["GET"])
def get_chat_history():
    return jsonify({"history": chat_history})

@chat_bp.route("/query", methods=["POST"])
def execute_query():
    data = request.json
    query = data.get("query")
    if not query:
        return jsonify({"error": "Query is required."}), 400
    
    schema = get_database_schema()
    if not schema:
        return jsonify({"error": "No database schema found."}), 400
    
    try:
        conn = sqlite3.connect("input\\dataset.db")
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        conn.close()
        
        explanation = f"Executed query: {query}"
        agent_steps = [
            {"id": str(uuid.uuid4()), "description": "Parsed user query", "status": "done"},
            {"id": str(uuid.uuid4()), "description": "Generated SQL query", "status": "done"},
            {"id": str(uuid.uuid4()), "description": "Executed query and retrieved results", "status": "done"}
        ]
        
        response = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "result": result,
            "columns": columns,
            "explanation": explanation,
            "agentSteps": agent_steps,
            "currentStep": len(agent_steps),
            "visualizationType": "table" if columns else "none",
            "followUpSuggestions": ["Show me more data", "Filter by a specific condition"]
        }
        
        chat_history.append(response)
        return jsonify(response)
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@chat_bp.route("/schema", methods=["GET"])
def get_schema():
    schema = get_database_schema()
    if not schema:
        return jsonify({"error": "No schema found."}), 400
    return jsonify(schema)