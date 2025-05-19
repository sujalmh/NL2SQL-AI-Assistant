from flask import request, jsonify, send_from_directory, Blueprint
import os
import sqlite3
import pandas as pd
from uuid import uuid4
from app.functions.gen_ai_doc import generate_report
from app.functions.gen_ai_graph import generate_visualization
from app.functions.gen_ai_ppt import generate_presentation
from app.functions.gen_ai import generate_relevant_prompts
from app.functions.gen_ai_visualise import visualise
from app.functions.gen_sql_query import generate_sql_query as get_sql_query
from pymongo import MongoClient
from datetime import datetime
import time
import requests
# Import functions from the uploaded modules
from app.functions.gen_ai_doc import generate_report as generate_pdf_report  
from app.functions.gen_ai_ppt import generate_presentation as generate_ppt_report
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

agent_bp = Blueprint('agent', __name__)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"] 

DOWNLOADS_FOLDER = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_FOLDER, exist_ok=True)
GRAPH_DIR = os.path.join(DOWNLOADS_FOLDER, 'graphs')
REPORT_DIR = os.path.join(DOWNLOADS_FOLDER, 'reports')
PPT_DIR = os.path.join(DOWNLOADS_FOLDER, 'presentations')

os.makedirs(GRAPH_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(PPT_DIR, exist_ok=True)


@agent_bp.route('/generate_report', methods=['POST'])
def generate_report():
    data = request.get_json()
    prompt = data.get('prompt')
    title = data.get('title')
    format = data.get('format', 'pdf').lower()
    chat_id = data.get('chatId')
    include_visualisataion = data.get('includeVisualisation', True)
    print("done 1")
    # Retrieve the file_path from MongoDB using chat_id
    file_record = db.projects.find_one({"chat_id": chat_id}, {"file_path": 1})
    if not file_record:
        return jsonify({"error": "No file found for the given chat_id"}), 404

    db_path = file_record.get("file_path")
    if not db_path:
        return jsonify({"error": "File path not found in the database record"}), 404
    print("done 2")
    # Retrieve the schema of the database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables: ", tables)
        sql_query = "SELECT name FROM sqlite_master WHERE type='table';"
        df = pd.read_sql_query(sql_query, conn)
        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema[table_name] = [{"name": col[1], "type": col[2]} for col in columns]
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve database schema: {str(e)}"}), 500
    print("done 3")
    print("Database Schema: ", schema)
    
    prompts = generate_relevant_prompts(prompt, df)
    print(prompts)
    print(chat_id)
    # Additional options can be processed here if needed

    # Validate required fields
    if not prompt or not title:
        return jsonify({"error": "Missing prompt or title"}), 400

    steps = []

    # Step 1: Analyze report requirements
    step1 = {"id": "1", "description": "Analyzing report requirements", "status": "completed"}
    steps.append(step1)
    time.sleep(1)  # Simulate delay
    
    
    payload = {
            "query": prompt,
            "chatId": chat_id,
            "graph": True
        }
    sql_query = None
    response = requests.post("http://localhost:8000/query", json=payload)
    if response.status_code == 200:
            json_data = response.json()
            sql_query = json_data.get("sql")

    
    print("Generated SQL Query 1: ", sql_query)
    try:
        conn = sqlite3.connect(db_path)
        print("done 4")
        try:
            df = pd.read_sql_query(sql_query, conn)
        except Exception as e:
            print("Error executing SQL query: ", e)
        
        print("done 5")
        conn.close()
        simulated_result = df.to_dict(orient='records')
        columns = [{"key": col, "label": col.replace("_", " ").title()} for col in df.columns]
    except Exception as e:
        return jsonify({"error": f"Database query failed: {str(e)}"}), 500

    # simulated_result = [
    #     {"product_name": "Product A", "total_sold": 1245},
    #     {"product_name": "Product B", "total_sold": 998},
    #     {"product_name": "Product C", "total_sold": 754},
    #     {"product_name": "Product D", "total_sold": 621},
    # ]
    # columns = [
    #     {"key": "product_name", "label": "Product Name"},
    #     {"key": "total_sold", "label": "Total Sold"},
    # ]

    print("Simulated Result: ", simulated_result)
    print("Columns: ", columns)
    step2 = {
        "id": "2",
        "description": "Generating SQL queries",
        "status": "completed",
        "sql": sql_query,
        "result": simulated_result,
        "columns": columns,
    }
    steps.append(step2)
    time.sleep(1.5)

    # Step 3: Create visualizations (simulation step)
    step3 = {"id": "3", "description": "Creating data visualizations", "status": "completed"}
    steps.append(step3)
    time.sleep(2)

    queries = []

    for pr in prompts:
        payload = {
            "query": pr,
            "chatId": chat_id,
            "graph": True  # You can set this based on the flow
        }
        response = requests.post("http://localhost:8000/query", json=payload)
        if response.status_code == 200:
            json_data = response.json()
            final_sql = json_data.get("sql")
            if final_sql:
                queries.append(final_sql)

    conn.close()
    
    graphs = []
    for qu in queries:
        g_name = f"{uuid4().hex}.png"
        output_path = os.path.join(GRAPH_DIR, g_name)
        try:
            conn = sqlite3.connect(db_path)
            df = pd.read_sql_query(qu, conn)
            conn.close()
        except Exception as e:
            print("Error executing SQL query: ", e)
            return jsonify({"error": f"Database query failed: {str(e)}"}), 500
        graph = visualise(df, output_path=output_path)
        if graph is not None:
            graphs.append(graph)
        
    print(graphs)

    # Step 4: Generate the report/presentation using the appropriate backend functions
    step4 = {"id": "4", "description": f"Compiling {format.upper()} report", "status": "processing"}
    steps.append(step4)
    time.sleep(1.5)

    # Create a dataframe from the simulated result
    df = pd.DataFrame(simulated_result)
    unique_name = uuid4().hex
    output_path = DOWNLOADS_FOLDER
    author = "Sujnan"
    print("Visualisation : ", include_visualisataion)
    try:
        if format == "pdf":
            output_path = f"{output_path}/reports/{unique_name}.{format}"
            # Generate PDF report using gen_ai_doc.py
            if include_visualisataion:
                generate_pdf_report(df, output_path, prompt, graphs=graphs,author=author, title=title)
            else:
                generate_pdf_report(df, output_path, prompt, graphs=[],author=author, title=title)
        elif format == "pptx":
            output_path = f"{output_path}/presentations/{unique_name}.{format}"
            # Generate PowerPoint presentation using gen_ai_ppt.py
            if include_visualisataion:
                generate_ppt_report(df, prompt, output_path, graphs=graphs, author=author, title=title)
            else:
                generate_ppt_report(df, prompt, output_path, graphs=[], author=author, title=title)
        else:
            return jsonify({"error": "Unsupported format"}), 400
    except Exception as e:
        step4["status"] = "error"
        return jsonify({"error": str(e), "steps": steps}), 500

    # Update step 4 to completed
    step4["status"] = "completed"
    steps[-1] = step4
    down_url = ""
    file_name = f"{unique_name}.{format}"
    # Prepare simulated preview data
    if format == "pdf":
        down_url += "/report/" + file_name
        
    else:
        down_url += "/presentation/" + file_name
        

    choice = "report" if format == "pdf" else "presentation"

    download_url = "http://localhost:5000/api/agent/download"+down_url

    preview_data = {"format": format, "downloadUrl": download_url,"choice": choice, "fileName": file_name}
    

    response = {
        "message": f"{format.upper()} report generated successfully",
        "steps": steps,
        "downloadUrl": download_url,
        "previewData": preview_data,
    }
    return jsonify(response), 200



@agent_bp.route('/exec_query', methods=['POST'])
def exec_query():
    data = request.json
    db_path = data.get('db_path')
    query = data.get('query')

    print(db_path,query)
    
    if not db_path or not query:
        return jsonify({'error': 'Missing db_path or query'}), 400

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_json(orient='records')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@agent_bp.route('/generate/<choice>', methods=['POST'])
def generate(choice):
    data = request.json
    db_path = data.get('db_path')
    query = data.get('query')
    query_goal = data.get('goal', 'Analyze the data and generate insights.')

    if not db_path or not query:
        return jsonify({'error': 'Missing db_path or query'}), 400

    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
    except Exception as e:
        return jsonify({'error': f'Database query failed: {str(e)}'}), 500

    filename = f"{uuid4().hex}"
    
    try:
        if choice == 'graph':
            filepath = os.path.join(GRAPH_DIR, f"{filename}.png")
            generate_visualization(df, output_path=filepath)

        elif choice == 'report':
            filepath = os.path.join(REPORT_DIR, f"{filename}.pdf")
            generate_report(df, filepath, query_goal)

        elif choice == 'presentation':
            filepath = os.path.join(PPT_DIR, f"{filename}.pptx")
            generate_presentation(df, query_goal, output_path=filepath)

        else:
            return jsonify({'error': 'Invalid generation type'}), 400
        
        log_entry = {
            "query": query,
            "choice": choice,
            "db_path": db_path,
            "query_output": df.to_dict(orient="records"),
            "gen_file_path": filepath,
            "generated_at": datetime.utcnow()
        }

        db.generated_files.insert_one(log_entry)

        return jsonify({'message': f"{choice.capitalize()} generated", 'filename': os.path.basename(filepath)})

    except Exception as e:
        return jsonify({'error': f'Failed to generate {choice}: {str(e)}'}), 500


@agent_bp.route('/download/<choice>/<filename>', methods=['GET'])
def download_file(choice, filename):
    if choice == 'graph':
        directory = GRAPH_DIR
    elif choice == 'report':
        directory = REPORT_DIR
    elif choice == 'presentation':
        directory = PPT_DIR
    else:
        return jsonify({'error': 'Invalid download type'}), 400
    print(directory)
    try:
        if filename.endswith(".pdf"):
            return send_from_directory(directory, filename, mimetype="application/pdf", as_attachment=False)
        elif filename.endswith(".pptx"):
            print("PPTX file :" , filename)
            return send_from_directory(directory, filename, mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation", as_attachment=False)
    except Exception as e:
        print("Error here : ",e)
        return jsonify({'error': 'File not found'}), 404
    

def get_llm_response(prompt):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",  # Adjust model as needed
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
        temperature=0.5
    )
    return completion.choices[0].message.content
    

def format_for_llm(schema, sample_data):
    prompt = "Database Schema:\n"
    for table, sql in schema.items():
        prompt += f"{sql}\n"
    
    prompt += "\nSample Data:\n"
    for table, data in sample_data.items():
        prompt += f"Table {table}:\n"
        for row in data:
            prompt += str(row) + "\n"
        prompt += "\n"
    
    prompt += (
        "Analyze the above database schema and sample data. Provide the following:\n"
        "1. SQL statements to create a normalized version of this database (in a ```sql code block).\n"
        "2. SQL statements to migrate the data from the original tables to the new normalized tables (in a separate ```sql code block).\n"
        "Ensure the output is formatted with ```sql markers for each section."
    )
    return prompt
    

def extract_schema_and_data(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Extract table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema = {}
    sample_data = {}
    
    for table in tables:
        # Extract schema
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}';")
        schema[table] = cursor.fetchone()[0]
        
        # Extract sample data (first 5 rows)
        cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
        sample_data[table] = cursor.fetchall()
    
    conn.close()
    return schema, sample_data
    

def normalize_sqlite_db(original_db_path, new_db_path, metadata_path):
    # Step 1: Extract schema and sample data
    schema, sample_data = extract_schema_and_data(original_db_path)
    
    # Step 2: Generate normalization plan and SQL via LLM
    prompt = format_for_llm(schema, sample_data)
    llm_response = get_llm_response(prompt)
    return llm_response
    


@agent_bp.route('/normalize', methods=['POST'])
def normalize_route():
    try:

        db_path = "input/fb8110cf-888b-41a5-a9bf-f3e66d837b56.db"

        if not db_path or not os.path.exists(db_path):
            return jsonify({"error": "Invalid or missing database path"}), 400

        new_db_path = 'normalized.db'
        metadata_path = 'schema_metadata.json'

        return jsonify({
            "message": "Normalization complete. Check your console for LLM output.",
            "output": normalize_sqlite_db(db_path, new_db_path, metadata_path)
        }), 200

    except Exception as e:
        print("Error during normalization: ", e)
        return jsonify({"error": str(e)}), 500
    




@agent_bp.route('/smart_prompt', methods=['POST'])
def generate_smart_prompt():
    try:
        data = request.get_json()
        chat_id = data.get("chatId")

        if not chat_id:
            return jsonify({"error": "Missing chat ID"}), 400

        project = db.projects.find_one({"chat_id": chat_id})
        if not project:
            return jsonify({"error": "Project not found"}), 404

        db_path = project.get("file_path")
        if not db_path or not os.path.exists(db_path):
            return jsonify({"error": "Database file not found"}), 404

        # Step 1: Extract schema from SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        schema = {}
        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            schema[table_name] = [{"name": col[1], "type": col[2]} for col in columns]
        conn.close()

        # Format schema for LLM
        formatted_schema = "\n".join([
            f"Table: {table}\n" + "\n".join([f" - {col['name']} ({col['type']})" for col in cols])
            for table, cols in schema.items()
        ])

        # Step 2: Prompt LLM
        prompt = f"""
You are a smart data assistant.

Here is a database schema:

{formatted_schema}

Generate ONE useful and simple report prompt for this data, for a user who wants quick insights. Be specific but general enough to work with the available fields. Do not hallucinate fields. 

Output the prompt as a single sentence only. No explanations.
"""

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7,
        )

        generated_prompt = completion.choices[0].message.content.strip()
        return jsonify({"prompt": generated_prompt}), 200

    except Exception as e:
        print("Prompt generation error:", e)
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


