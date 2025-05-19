import os
import re
import sqlite3  # or use your actual DB connector
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

def generate_sql_query(nl_query: str, db_schema: str, db_connection, model_name="gpt-4o-mini", max_retries=10) -> str:
    """
    Convert a natural language query into a valid SQL query using OpenAI and LangChain, retrying on execution errors.

    Args:
        nl_query (str): Natural language query describing the desired data retrieval.
        db_schema (str): Description of the database schema (tables, fields, relationships).
        db_connection: Database connection object.
        model_name (str): OpenAI model to use.
        max_retries (int): Max number of retry attempts.

    Returns:
        str: Valid SQL query or None.
    """
    print("db Schama : ",db_schema)
    llm = ChatOpenAI(model=model_name, temperature=0.2, api_key=openai_api_key)
    parser = StrOutputParser()

    for attempt in range(1, max_retries + 1):
        print(f"\n🌀 Attempt {attempt}: Generating SQL query...")

        # Include the error message only from second attempt onward
        error_context = ""
        if attempt > 1:
            error_context = f"\n\n### Previous Error:\n{last_error}\ntry to fix it."

        prompt_template = PromptTemplate.from_template(
            f"""
            You are an expert SQL developer.

            ### Task:
            Convert the natural language query into a correct and efficient SQL query using the provided schema.
            Make sure the query runs successfully on execution.

            ### Database Schema:
            {db_schema}

            ### Natural Language Query:
            {nl_query}
            {error_context}

            ### Output Format:
            Return only the SQL query enclosed in triple backticks with the tag `query` like this:

            ```query
            SELECT * FROM ...
            ```
            """
        )


        try:
            prompt = prompt_template.format(
                nl_query=nl_query,
                db_schema=db_schema,
                error_context=error_context
            )
            # print("Prompt:", prompt)
            response = llm.invoke(prompt)
            output = parser.invoke(response)

            # Extract SQL
            sql_match = re.search(r"```query\n(.*?)```", output, re.DOTALL)
            if not sql_match:
                print("❌ No valid SQL code block found.")
                continue

            sql_query = sql_match.group(1).strip()

            # ✅ Try executing the SQL
            cursor = db_connection.cursor()
            cursor.execute(sql_query)
            db_connection.commit()
            print("✅ SQL executed successfully.")
            return sql_query

        except Exception as e:
            last_error = str(e)
            print(f"⚠️ SQL execution failed with error:\n{last_error}")

    print("❌ Max retries reached. Could not generate a valid SQL query.")
    return None
