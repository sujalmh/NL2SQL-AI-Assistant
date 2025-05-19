from datetime import datetime
from flask import Blueprint, request, jsonify
import sqlite3
import csv
import json
import io
import os 
from pymongo import MongoClient
import uuid
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.exc import SQLAlchemyError
import uuid
import pandas as pd
import sqlite3
import os
import pymysql
import json
from sqlalchemy import create_engine, MetaData, inspect
import os
from dotenv import load_dotenv
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"] 
chat_collection = db.chats

upload_bp = Blueprint('upload', __name__)
INPUT_FOLDER = "input"
os.makedirs(INPUT_FOLDER, exist_ok=True)

def get_next_project_id():
    counter = db.counters.find_one_and_update(
        {"_id": "project_id"},
        {"$inc": {"sequence_value": 1}},
        return_document=True
    )
    if counter is None:
        db.counters.insert_one({"_id": "project_id", "sequence_value": 1})
        return 1
    return counter["sequence_value"]

def get_file_type(filename):
    filename = filename.lower()
    if filename.endswith(".csv"): return "csv"
    if filename.endswith(".json"): return "json"
    if filename.endswith(".sql") or filename.endswith(".db"): return "sql"
    raise ValueError("Unsupported file format. Please upload a CSV, JSON, or SQL file.")

def save_file(file, default_extension=".db"):
    # Try to get the filename attribute; if not present, fall back to a default name.
    if hasattr(file, 'filename'):
        original_filename = file.filename
        ext = os.path.splitext(original_filename)[1]
    else:
        # If there's no filename attribute, assign a default filename and extension.
        original_filename = f"uploaded{default_extension}"
        ext = default_extension

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(INPUT_FOLDER, unique_filename)

    # If the file object has a save method (like Flask's FileStorage), use it.
    if hasattr(file, 'save'):
        file.save(file_path)
    else:
        # Otherwise, treat it as a regular file-like object.
        file.seek(0)  # Ensure we're at the beginning of the file.
        with open(file_path, 'wb') as f_out:
            f_out.write(file.read())

    return file_path, original_filename

def parse_csv_and_data_to_db(file, chat_id, user_id):
    csv_path, original_filename  = save_file(file)
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    # Read the CSV into a DataFrame
    df = pd.read_csv(csv_path)
    sqlite_path = os.path.join(INPUT_FOLDER, f"{str(uuid.uuid4())}.db")
    # Connect to SQLite (creates the DB file if it doesn't exist)
    conn = sqlite3.connect(sqlite_path)
    table_name = original_filename.replace(".csv", "")
    try:
        # Write the DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Table '{table_name}' created in SQLite database at: {sqlite_path}")
    finally:
        conn.close()

    return update_schema_and_data_to_db(open(sqlite_path, 'rb'), chat_id, user_id)

def parse_csv(file):
    csv_path, original_filename  = save_file(file)
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found at: {csv_path}")

    # Read the CSV into a DataFrame
    df = pd.read_csv(csv_path)
    sqlite_path = os.path.join(INPUT_FOLDER, f"{str(uuid.uuid4())}.db")
    # Connect to SQLite (creates the DB file if it doesn't exist)
    conn = sqlite3.connect(sqlite_path)
    table_name = original_filename.replace(".csv", "")
    try:
        # Write the DataFrame to SQLite
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Table '{table_name}' created in SQLite database at: {sqlite_path}")
    finally:
        conn.close()

    return parse_database_file(open(sqlite_path, 'rb'))

def parse_json(file):
    file_path, original_filename = save_file(file)

    with open(file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    schema = json_data.get("schema", {})
    data = json_data.get("data", {})

    sqlite_path = os.path.join(INPUT_FOLDER, f"{str(uuid.uuid4())}.db")
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Create tables and insert data
    for table_name, columns in schema.items():
        column_defs = []
        for col in columns:
            col_type = col["type"]
            nullable = "" if col["nullable"] else "NOT NULL"
            column_defs.append(f"{col['name']} {col_type} {nullable}")
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)});"
        cursor.execute(create_stmt)

        # Insert data if available
        table_data = data.get(table_name, [])
        if table_data:
            col_names = table_data[0].keys()
            placeholders = ", ".join(["?"] * len(col_names))
            insert_stmt = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
            values = [tuple(row[col] for col in col_names) for row in table_data]
            cursor.executemany(insert_stmt, values)

    conn.commit()
    conn.close()

    # Return parsed result from the created SQLite DB
    return parse_database_file(open(sqlite_path, 'rb'))

def parse_json_and_data_to_db(file, chat_id, user_id):
    file_path, original_filename = save_file(file)

    with open(file_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)

    schema = json_data.get("schema", {})
    data = json_data.get("data", {})

    sqlite_path = os.path.join(INPUT_FOLDER, f"{str(uuid.uuid4())}.db")
    conn = sqlite3.connect(sqlite_path)
    cursor = conn.cursor()

    # Create tables and insert data
    for table_name, columns in schema.items():
        column_defs = []
        for col in columns:
            col_type = col["type"]
            nullable = "" if col["nullable"] else "NOT NULL"
            column_defs.append(f"{col['name']} {col_type} {nullable}")
        create_stmt = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)});"
        cursor.execute(create_stmt)

        # Insert data if available
        table_data = data.get(table_name, [])
        if table_data:
            col_names = table_data[0].keys()
            placeholders = ", ".join(["?"] * len(col_names))
            insert_stmt = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({placeholders})"
            values = [tuple(row[col] for col in col_names) for row in table_data]
            cursor.executemany(insert_stmt, values)

    conn.commit()
    conn.close()
    return update_schema_and_data_to_db(open(sqlite_path, 'rb'), chat_id, user_id)

def update_schema_and_data_to_db(file, chat_id, user_id):
    file_path, original_filename = save_file(file)
    filename_lower = original_filename.lower()

    db_name = original_filename.replace(".db", "").replace(".sqlite", "").replace(".sql", "")

    if filename_lower.endswith((".db", ".sqlite")):
        connection_string = f"sqlite:///{file_path}"
    elif filename_lower.endswith(".sql"):
        return mysql_to_json_and_data_to_db(file, chat_id, user_id)
    else:
        raise ValueError("Unsupported SQL file format. Please upload a SQLite database file or a SQL dump file.")

    engine = create_engine(connection_string)

    if filename_lower.endswith(".sql"):
        with open(file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except SQLAlchemyError as e:
                    raise ValueError(f"Error executing SQL statement: {e}")

    metadata = MetaData()
    try:
        metadata.reflect(bind=engine)
        if not metadata.tables:
            raise ValueError("No tables found in the database.")
    except Exception as e:
        raise ValueError(f"Error reflecting database schema: {e}")

    schema = {
        table_name: [
            {
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable
            } for col in table_obj.columns
        ]
        for table_name, table_obj in metadata.tables.items()
    }

    data = {}
    with engine.connect() as conn:
        for table_name, table_obj in metadata.tables.items():
            query = table_obj.select().limit(1000)
            result_proxy = conn.execute(query)
            rows = result_proxy.fetchall()
            column_names = result_proxy.keys()
            data[table_name] = [dict(zip(column_names, row)) for row in rows]

    project_id = get_next_project_id()

    database_entry = {
        "file_path": file_path,
        "original_filename": original_filename,
        "db_name": db_name,
        "tables": [
            {"table_name": table_name, "columns": [col["name"] for col in schema[table_name]]}
            for table_name in schema
        ],
        "data": data
    }

    project_document = {
        "_id": project_id,
        "user_id": user_id,
        "name": db_name,
        "chat_id": chat_id,
        "original_filename": original_filename,
        "file_path": file_path,
        "description": f"Database project for {db_name}",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "database_uploaded": True,
        "database_details": database_entry,
        "status": "active",
        "shared_with": [],
        "last_accessed": datetime.utcnow()
    }
    db.projects.insert_one(project_document)

    return {"project_id": project_id, "schema": schema, "data": data}

def parse_database_file(file):
    file_path, orignal_filename = save_file(file)
    filename_lower = orignal_filename.lower()

    if filename_lower.endswith((".db", ".sqlite")):
        connection_string = f"sqlite:///{file_path}"
    elif filename_lower.endswith(".sql"):
        return mysql_to_json("localhost", "root", "mnbvcx12", orignal_filename.lower())
    else:
        raise ValueError("Unsupported SQL file format. Please upload a SQLite database file or a SQL dump file.")

    engine = create_engine(connection_string)

    if filename_lower.endswith(".sql"):
        with open(file_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
        with engine.begin() as conn:
            for stmt in statements:
                try:
                    conn.execute(text(stmt))
                except SQLAlchemyError as e:
                    raise ValueError(f"Error executing SQL statement: {e}")

    metadata = MetaData()
    try:
        metadata.reflect(bind=engine)
        if not metadata.tables:
            raise ValueError("No tables found in the database.")
    except Exception as e:
        raise ValueError(f"Error reflecting database schema: {e}")

    schema = {
        table_name: [
            {
                "name": col.name,
                "type": str(col.type),
                "nullable": col.nullable
            } for col in table_obj.columns
        ]
        for table_name, table_obj in metadata.tables.items()
    }

    data = {}
    with engine.connect() as conn:
        for table_name, table_obj in metadata.tables.items():
            query = table_obj.select().limit(1000)
            result_proxy = conn.execute(query)
            rows = result_proxy.fetchall()
            column_names = result_proxy.keys()
            data[table_name] = [dict(zip(column_names, row)) for row in rows]

    return { "schema": schema, "data": data}

def mysql_to_json(host, user, password, database, port=3306, output_path=f"input/{str(uuid.uuid4())}.json"):
    # Create SQLAlchemy engine
    connection_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(connection_url)

    inspector = inspect(engine)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    schema = {}
    data = {}

    for table_name in inspector.get_table_names():
        # Schema
        columns = inspector.get_columns(table_name)
        schema[table_name] = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"]
            }
            for col in columns
        ]

        # Data
        with engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM `{table_name}`")
            rows = result.fetchall()
            col_names = result.keys()
            data[table_name] = [dict(zip(col_names, row)) for row in rows]

    result_json = {
        "schema": schema,
        "data": data
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)

    return parse_json(output_path)

def mysql_to_json_and_data_to_db(host, user, password, database, chat_id, user_id, port=3306, output_path=f"input/{str(uuid.uuid4())}.json"):
    # Create SQLAlchemy engine
    connection_url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(connection_url)

    inspector = inspect(engine)
    metadata = MetaData()
    metadata.reflect(bind=engine)

    schema = {}
    data = {}

    for table_name in inspector.get_table_names():
        # Schema
        columns = inspector.get_columns(table_name)
        schema[table_name] = [
            {
                "name": col["name"],
                "type": str(col["type"]),
                "nullable": col["nullable"]
            }
            for col in columns
        ]

        # Data
        with engine.connect() as conn:
            result = conn.execute(f"SELECT * FROM `{table_name}`")
            rows = result.fetchall()
            col_names = result.keys()
            data[table_name] = [dict(zip(col_names, row)) for row in rows]

    result_json = {
        "schema": schema,
        "data": data
    }

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result_json, f, indent=2, ensure_ascii=False)

    return parse_json(output_path, chat_id, user_id)


@upload_bp.route('/start', methods=['GET', 'POST'])
def store_schema():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    
    user_id = int(request.form.get("user_id"))
    chat_id = request.form.get("chat_id")

    filename_lower = file.filename.lower()
    try:
        if filename_lower.endswith(".csv"):
            result = parse_csv_and_data_to_db(file, chat_id, user_id)
        elif filename_lower.endswith(".json"):
            result = parse_json_and_data_to_db(file, chat_id, user_id)
        elif filename_lower.endswith((".db", ".sqlite", ".sql")):
            result = update_schema_and_data_to_db(file, chat_id, user_id)
        else:
            return jsonify({"error": "Unsupported file format"}), 400
        schema = result.get("schema", {})
        table_count = len(schema)

        agent_steps = [
            {
                "id": str(uuid.uuid4()),
                "description": "Database file processed successfully",
                "status": "done"
            },
            {
                "id": str(uuid.uuid4()),
                "description": f"Detected {table_count} tables",
                "status": "done"
            },
            *[
                {
                    "id": str(uuid.uuid4()),
                    "description": f'Table "{table}" with {len(columns)} columns',
                    "status": "done"
                }
                for table, columns in schema.items()
            ],
            {
                "id": str(uuid.uuid4()),
                "description": "Ready to answer questions about your data",
                "status": "done"
            }
        ]

        assistant_message = {
            "id": str(uuid.uuid4()),
            "chat_id": chat_id,
            "role": "assistant",
            "content": "Database uploaded successfully! You can now ask questions about your data.",
            "timestamp": datetime.utcnow(),
            "agentSteps": agent_steps,
            "currentStep": len(agent_steps),
            "explanation": "I've analyzed your database and I'm ready to help you query it.",
            "followUpSuggestions": [
                "Show me the schema",
                "List all tables",
                "How many rows are in each table?"
            ]
        }
        chat_collection.insert_one(assistant_message)

        return jsonify(result)
    except Exception as e:
        print(f"Error: {str(e)}")  
        return jsonify({"error": str(e)}), 400

@upload_bp.route('/', methods=['GET', 'POST'])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    filename_lower = file.filename.lower()
    try:
        if filename_lower.endswith(".csv"):
            result = parse_csv(file)
        elif filename_lower.endswith(".json"):
            result = parse_json(file)
        elif filename_lower.endswith((".db", ".sqlite", ".sql")):
            result = parse_database_file(file)
        else:
            return jsonify({"error": "Unsupported file format"}), 400
        return jsonify(result)
    except Exception as e:
        print(f"Error: {str(e)}")  
        return jsonify({"error": str(e)}), 400
