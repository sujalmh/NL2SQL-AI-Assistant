from flask import Flask
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from app.config import Config
from app.routes.upload import upload_bp
from app.routes.chat import chat_bp
from app.routes.auth import auth_bp
from app.routes.project import project_bp
from app.routes.audio import audio_bp
from app.routes.agents import agent_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(upload_bp, url_prefix='/api/upload')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(project_bp, url_prefix='/api/project')
    app.register_blueprint(agent_bp, url_prefix='/api/agent')
    app.register_blueprint(audio_bp, url_prefix='/api/audio')
    
    app.config.from_object(Config)

    mongo_client = MongoClient(app.config["MONGO_URI"], server_api=ServerApi("1"))

    # Select the database
    database_name = "try1"  # Replace with your actual database name
    app.db = mongo_client[database_name]

    # Define a collection (e.g., "users")
    app.users_collection = app.db["users"]

    CORS(app)
    return app