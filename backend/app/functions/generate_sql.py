import asyncio
from typing import List, Dict, Optional
from sqlalchemy import text
from langchain_openai import ChatOpenAI
from langchain.chains import create_sql_query_chain
from langchain_community.utilities import SQLDatabase
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Define the initial prompt and examples (same as your original)
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
    input_variables=['input', 'table_info', 'sample_data', 'top_k', 'history'],
    prefix=(
        "You are an AI assistant that generates valid SQLite queries given a multi-table database. "
        "Use the conversation history for context. Only output the SQL query.\n\n"
        "Conversation History:\n{history}\n\n"
        "Database schema (all tables):\n{table_info}\n\n"
        "Sample rows from each table:\n{sample_data}\n"
    ),
    suffix=(
        "Top K rows: {top_k}\n"
        "Current question: {input}\n"
        "SQLQuery:"
    )
)

# Create a shared LLM instance; you can adjust the model settings as needed
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
# llm = ChatGoogleGenerativeAI(
#     model="gemini-2.0-flash",    temperature=0
# )


# Define the state type as a Python dictionary.
def init_state(question: str) -> Dict:
    return {
        'question': question,
        'history': [],
        'sql_query': "",
        'result': None,
        'retries': 0
    }

async def async_query(query: str, db_type: str, db_url: str) -> List[Dict]:
    """
    Asynchronously process a SQL query generation and execution with retries.
    
    Parameters:
      - query (str): The natural language query.
      - db_type (str): The type of database. (Currently only "sqlite" is handled.)
      - db_url (str): The URI/path for connecting to the database.
    
    Returns:
      A list of steps (as dictionaries) representing what occurred on each step,
      including any retries and the final result.
    """
    steps: List[Dict] = []

    # Step 1: Connect to the database. You can extend this branch based on db_type if needed.
    if db_type.lower() == "sqlite":
        db = SQLDatabase.from_uri(f"sqlite:///{db_url}")
    else:
        raise ValueError("Only 'sqlite' database type is currently supported.")

    # Get schema and sample data
    table_info_str = db.get_table_info()
    sample_data = {}
    tables = db.get_usable_table_names()
    for tbl in tables:
        try:
            cursor = db.run(f"SELECT * FROM {tbl} LIMIT 5;", fetch="cursor")
            rows = cursor.mappings()
            sample_data[tbl] = [dict(r) for r in rows]
        except Exception:
            sample_data[tbl] = []

    steps.append({
        "step": "load_database",
        "message": "Database loaded successfully",
        "tables": tables,
        "table_info": table_info_str,
        "sample_data": sample_data
    })

    # Initialize state
    state = init_state(query)

    # Retry loop with a limit of 3 retries
    MAX_RETRIES = 3

    while True:
        # Step 2: Generate SQL query using the LLM chain.
        chain = create_sql_query_chain(
            llm=llm,
            db=db,
            prompt=PROMPT,
            k=5
        )
        # Prepare the input; note that we take only the last HISTORY_WINDOW_SIZE lines.
        HISTORY_WINDOW_SIZE = 10
        inp = {
            "question": state["question"],
            "history": "\n".join(state['history'][-HISTORY_WINDOW_SIZE:]),
            "table_info": table_info_str,
            "sample_data": sample_data,
            "top_k": 5
        }
        # Here we wrap the synchronous call in asyncio.to_thread to avoid blocking.
        sql_query = await asyncio.to_thread(chain.invoke, inp)
        # Cleanup possible markdown formatting
        if sql_query.strip().startswith("```"):
            sql_query = sql_query.strip("```").replace("sql", "").strip()
        state["sql_query"] = sql_query
        steps.append({
            "step": "generate_query",
            "sql_query": sql_query
        })

        # Step 3: Execute the SQL query.
        try:
            cursor = db.run(text(sql_query), fetch="cursor")
            raw_rows = list(cursor.mappings())
            rows = [dict(r) for r in raw_rows]
            columns = list(rows[0].keys()) if rows else []
            state["result"] = {"columns": columns, "data": rows}
            steps.append({
                "step": "execute_query",
                "result": state["result"]
            })
        except Exception as e:
            error_msg = str(e)
            state["result"] = {"error": error_msg}
            steps.append({
                "step": "execute_query",
                "error": error_msg
            })

        # Check if there was an SQL error and whether we should retry
        if "error" in state["result"] and state["retries"] < MAX_RETRIES:
            state["retries"] += 1
            retry_message = f"Retry {state['retries']}: SQL error encountered: {state['result']['error']}"
            state["history"].append(retry_message)
            steps.append({
                "step": "retry",
                "message": retry_message,
                "history": state["history"],
                "retries": state["retries"]
            })
            # Optionally, yield control to let the caller process the step
            await asyncio.sleep(0)
        else:
            # No error or reached maximum retries.
            break

    return steps