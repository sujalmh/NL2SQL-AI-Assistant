from openai import OpenAI
from flask import Blueprint, request, send_file, jsonify
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import io
import tempfile
from pathlib import Path

load_dotenv()

client = OpenAI()


MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["try1"]
users_collection = db["users"]

audio_bp = Blueprint('audio', __name__)

@audio_bp.route('/transcribe', methods=['POST'])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    uploaded_file = request.files['file']
    audio_bytes = uploaded_file.read()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = uploaded_file.filename

    print(audio_file.name)
    try:
        transcript = client.audio.translations.create(model="whisper-1", file=audio_file, response_format="text"
)
        return jsonify({"transcript": transcript})
    except Exception as e:
        print(f"Error during transcription: {e}")
        return jsonify({"error": str(e)}), 500

@audio_bp.route('/speech', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json()

        text = data.get("text")

        if not text:
            return jsonify({"error": "Missing 'text' in request body"}), 400

        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmpfile:
            audio_path = Path(tmpfile.name)

        # Stream TTS response to file
        with client.audio.speech.with_streaming_response.create(
            model="gpt-4o-mini-tts",
            voice="coral",
            input=text,
            instructions="Speak in a cheerful and positive tone.",
        ) as response:
            response.stream_to_file(audio_path)

        # Send audio file to client
        return send_file(
            audio_path,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name="speech.mp3"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500
