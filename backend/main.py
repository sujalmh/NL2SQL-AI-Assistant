from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from app.functions.explaination import generate_nl_explanation
from app.functions.generate_sql import async_query
import uuid
from app.functions.explaination import thinking_explanation
from datetime import datetime
from app.functions.visualize_with_db import visualise
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()

# MongoDB Setup
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["try1"] 
chat_collection = db.chats
OUTPUT_FOLDER = "output/visualization"
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)


# FastAPI Setup
app = FastAPI()
app.mount("/visualization", StaticFiles(directory=OUTPUT_FOLDER), name="visualizations")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request model
class QueryRequest(BaseModel):
    query: str
    chatId: str
    graph: bool

@app.post("/query")
async def execute_query(payload: QueryRequest):
    query = payload.query
    chat_id = payload.chatId
    graph = payload.graph
    print(graph)
    project = await db.projects.find_one({"chat_id": chat_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    db_file_path = project.get("file_path")
    db_type = "sqlite" if db_file_path.endswith(".db") else "mysql"

    if db_type != "sqlite":
        raise HTTPException(status_code=400, detail="Only SQLite is currently supported.")

    try:
        # Run SQL generation and execution steps
        if not graph:
            try:
                user_chat_doc = {
                    "id": str(uuid.uuid4()),
                    "role": "user",
                    "content": query,
                    "timestamp": datetime.utcnow(),
                    "chat_id": chat_id
                }

                await chat_collection.insert_one(user_chat_doc)
            except:
                raise HTTPException(status_code=500, detail="Error inserting user chat document")
            
        steps = await async_query(query, db_type, db_file_path)
        print(steps)
        agentThinking = []
        final_sql = None
        result = None
        schema = None
        for step in steps:
            agentThinking.append({"id": str(uuid.uuid4()), "description": thinking_explanation(str(step)), "status": "done"})
            if step["step"] == "generate_query":
                
                final_sql = step["sql_query"]
            elif step["step"] == "execute_query":
                try:
                    result = step["result"]
                except:
                    continue
            elif step["step"] == "load_database":
                db_details = step["table_info"]
                sample_data = step["sample_data"]
        if not result:
            raise HTTPException(status_code=500, detail="No result from query execution")

        # Generate natural language explanation
        explanation = generate_nl_explanation(query, result)

        out_file_name = f"{str(uuid.uuid4())}.png"
        out_file_path = OUTPUT_FOLDER+"/"+out_file_name
        visualise(result, out_file_path)

        columns = []
        for col in result["columns"]:
            columns.append({"key": col, "label": col})
        result["columns"] = columns
        
        try:
            if not graph:
                chat_document = {
                    "id": str(uuid.uuid4()),  # Chat identifier (optional field)
                    "chat_id": chat_id,        # Chat ID to associate with the user
                    "role": "assistant",        # Role: "user" or "assistant"
                    "content": explanation,     # This could also include a summary of the SQL query or additional context
                    "timestamp": datetime.utcnow(),  # UTC datetime timestamp
                    "agentSteps": agentThinking,      # Steps generated during execution
                    "currentStep": len(agentThinking),              # (Optional) current step index if you plan to update live progress
                    "sqlQuery": final_sql,            # The final SQL query generated
                    "explanation": explanation,       # Generated natural language explanation of the result
                    "tableData": result["data"],  # Table data; adjust key as needed based on your result structure
                    "tableColumns": columns,             # Table columns formatted as key/label pairs
                    "visualization": "http://127.0.0.1:8000/visualization/"+out_file_name,  # Path to the visualization image
                }
                
                await chat_collection.insert_one(chat_document)
        except:
            raise HTTPException(status_code=500, detail="Error inserting chat document")

        return {
            "steps": agentThinking,
            "sql": final_sql,
            "result": result,
            "explanation": explanation,
            "visualization": "http://127.0.0.1:8000/visualization/"+out_file_name
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
