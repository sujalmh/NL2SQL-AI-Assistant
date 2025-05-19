import os
import openai
import json
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from typing import List

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class SubPromptResponse(BaseModel):
    sub_prompts: List[str]


def generate_relevant_prompts(user_prompt: str, schema: dict | pd.DataFrame, model_name="gpt-4o-mini") -> list:
    if isinstance(schema, pd.DataFrame):
        schema_dict = schema.dtypes.apply(lambda x: x.name).to_dict()
        schema_string = json.dumps({"table_name": schema_dict}, indent=2)
    else:
        schema_string = json.dumps(schema, indent=2)

    instructions = """
You are a highly skilled data analyst assistant.

### Task:
Extract useful, clear, and structured sub-prompts for data reporting or visualization purposes, based on the provided user prompt and database schema.

### Rules:
- Only use fields mentioned in the schema.
- No hallucinations or invented fields.
- Output sub-prompts as plain, readable strings that can be used to generate reports or visualizations.
"""

    user_input = f"""
User Prompt:
"{user_prompt}"

Database Schema:
{schema_string}
"""


    try:
        print(f"🌀 Generating structured sub-prompts for: '{user_prompt}'...")

        response = client.beta.chat.completions.parse(
            model=model_name,
            messages=[{ "role": "user", "content": instructions }],
            response_format=SubPromptResponse,
            temperature=0.3
        )
        
        result = response.choices[0].message.parsed.sub_prompts

        print("✅ Structured sub-prompts:", result)
        return result

    except Exception as e:
        print(f"🚨 Error during structured prompt generation: {e}")
        return []
