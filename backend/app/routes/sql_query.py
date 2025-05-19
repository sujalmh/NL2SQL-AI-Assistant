from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Dict
from sqlalchemy import text
from dotenv import load_dotenv
import logging

# Load env vars
load_dotenv()

app = Flask(_name_)
CORS(app)

# Config
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'db'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Globals
db: Optional[SQLDatabase] = None
table_info_str: str = ""
sample_data: Dict[str, List[Dict]] = {}
llm_history: List[str] = []
HISTORY_WINDOW_SIZE = 10

# LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

# State type
class QueryState(TypedDict):
    question: str
    history: List[str]
    sql_query: str
    result: Optional[dict]
    retries: int

# Placeholder examples
examples = [
    {
        "input": "New question: list recent entries from table1",
        "answer": "SELECT * FROM table1 ORDER BY created_at DESC LIMIT 5;"
    },
    {
        "input": "Continue question: filter above by status = 'active'",
        "answer": "SELECT * FROM table1 WHERE status = 'active' ORDER BY created_at DESC LIMIT 5;"
    }
]

example_prompt = PromptTemplate(
    input_variables=["input", "answer"],
    template="Question: {input}\nSQLQuery: {answer}"
)

PROMPT = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    input_variables=['input', 'table_info', 'sample_data', 'top_k', 'history'],  # Added history
    prefix="""
            You are an AI assistant that generates valid SQLite queries given a multi-table database. 
            Use the conversation history for context. Only output the SQL query.

            Conversation History:
            {history}

            Database schema (all tables):
            {table_info}

            Sample rows from each table:
            {sample_data}
            """,
    suffix="""
        Top K rows: {top_k}
        Current question: {input}
        SQLQuery:"""
)

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/api/upload', methods=['POST'])
def upload_file():
    global db, table_info_str, sample_data

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    # Save and load DB
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    db = SQLDatabase.from_uri(f"sqlite:///{filepath}")

    # Get full schema description string
    table_info_str = db.get_table_info()

    # Collect up to 5 sample rows per table
    sample_data = {}
    tables = db.get_usable_table_names()
    for tbl in tables:
        cursor = db.run(f"SELECT * FROM {tbl} LIMIT 5;", fetch="cursor")
        rows = cursor.mappings()
        sample_data[tbl] = [dict(r) for r in rows]

    return jsonify({'message': 'Database uploaded', 'tables': tables}), 200

@app.route('/api/ask', methods=['POST'])
def ask_question():
    global db, table_info_str, sample_data
    if not db:
        return jsonify({'error': 'Database not uploaded'}), 400

    data = request.json or {}
    question = data.get('question')
    history = data.get('history', [])
    if not question:
        return jsonify({'error': 'No question provided'}), 400

    # Initialize state with fresh retry counter
    state: QueryState = {
        'question': question,
        'history': history,
        'sql_query': "",
        'result': None,
        'retries': 0  # Initialize retry counter
    }

    graph = create_graph()
    try:
        out = graph.invoke(state)
        print(f"Graph output: {out}")
        return jsonify({
            'sql_query': out['sql_query'],
            'result': out['result'],
            'history': out['history']
        })
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

def create_graph():
    def gen_query(state: QueryState) -> QueryState:
        chain = create_sql_query_chain(
            llm=llm,
            db=db,
            prompt=PROMPT,
            k=5
        )
        inp = {
            "question": state["question"],
            # Use state's history including errors
            "history": "\n".join(state['history'][-HISTORY_WINDOW_SIZE:]),  
            "table_info": table_info_str,
            "sample_data": sample_data,
            "top_k": 5
        }
        resp = chain.invoke(inp)

        if resp.startswith(""):
            resp = resp.strip("").replace("sql", "")
        return {**state, 'sql_query': resp}

    def exec_query(state: QueryState) -> QueryState:
        try:
            cursor = db.run(text(state['sql_query']), fetch="cursor")
            # Consume the MappingResult into a list
            # pull all rows into a list of dicts
            raw_rows = list(cursor.mappings())
            rows = [dict(r) for r in raw_rows]

            if rows:
                cols = list(rows[0].keys())
                data = rows
            else:
                cols, data = [], []

            
            return {**state, 'result': {'columns': cols, 'data': data}}
        except Exception as e:
            return {**state, 'result': {'error': str(e)}}


    def prep_retry(state: QueryState) -> QueryState:
        error_msg = f"Previous SQL error: {state['result']['error']}"
        return {
            **state,
            'retries': state['retries'] + 1,
            'history': state['history'] + [error_msg],
            'result': None
        }

    def should_retry(state: QueryState) -> bool:
        has_error = 'error' in (state.get('result') or {})
        under_retry_limit = state.get('retries', 0) < 3
        return has_error and under_retry_limit

    # Build the graph
    g = StateGraph(QueryState)
    g.add_node('generate', gen_query)
    g.add_node('execute', exec_query)
    g.add_node('retry', prep_retry)
    
    g.set_entry_point('generate')
    g.add_edge('generate', 'execute')
    g.add_conditional_edges(
        'execute',
        should_retry,
        {True: 'retry', False: END}
    )
    g.add_edge('retry', 'generate')
    
    return g.compile()

if _name_ == '_main_':
    logging.basicConfig(level=logging.INFO)
    app.run(debug=True)
