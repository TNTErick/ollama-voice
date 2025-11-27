import os
import uuid
import tempfile
import logging
import subprocess
import sys
from flask import Flask, render_template, request, jsonify, url_for
import whisper
import ollama
import pyttsx3
import pythoncom  # Required for Windows TTS to work in Flask threads

# --- CONFIGURATION ---
# Example: "com.apple.speech.synthesis.voice.ting-ting" or Windows Registry ID
VOICE_ID = None 
# ---------------------

app = Flask(__name__)

# Ensure audio folder exists
STATIC_AUDIO_DIR = os.path.join(os.getcwd(), 'static', 'audio')
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)

print("Loading Whisper...")
whisper_model = whisper.load_model("base")
print("✅ Whisper Ready")

# --- SAFE TTS GENERATION (In-Process) ---
# Uses pythoncom to initialize the Windows voice engine on this specific thread.
def generate_audio_file(text, output_path):
    try:
        # 1. Initialize Windows COM
        pythoncom.CoInitialize()
        
        # 2. Create engine
        engine = pyttsx3.init()
        engine.setProperty('rate', 175)
        
        if VOICE_ID:
            try:
                engine.setProperty('voice', VOICE_ID)
            except:
                pass

        # 3. Save
        engine.save_to_file(text, output_path)
        engine.runAndWait()
        
    except Exception as e:
        print(f"TTS Engine Error: {e}")
        raise e
    finally:
        # 4. Cleanup Windows COM
        pythoncom.CoUninitialize()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio part'}), 400

    audio_file = request.files['audio']
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        audio_file.save(temp.name)
        temp_path = temp.name

    try:
        print("🎧 Transcribing...")
        result = whisper_model.transcribe(temp_path, fp16=False)
        text = result['text'].strip()
        print(f"🗣️ User said: {text}")
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_text = data.get('text')
        
        if not user_text:
            return jsonify({'error': 'No text provided'}), 400

        # 1. Get AI Response
        print(f"🤖 Sending to Ollama: {user_text}")
        
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': user_text}])
        ai_text = response['message']['content']
        
        print(f"✅ Ollama replied: {ai_text[:50]}...")

        # 2. Generate Audio
        filename = f"response_{uuid.uuid4().hex}.wav"
        save_path = os.path.join(STATIC_AUDIO_DIR, filename)

        print("🔊 Generating Audio...")
        generate_audio_file(ai_text, save_path)

        # 3. Return result
        audio_url = url_for('static', filename=f'audio/{filename}')
        
        return jsonify({
            'response': ai_text, 
            'audio_url': audio_url
        })

    except Exception as e:
        print(f"❌ Server Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    try:
        # SSL context required for Mobile Mic
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
    except:
        print("⚠️ SSL Failed. Mic might not work on mobile.")
        app.run(host='0.0.0.0', port=5000, debug=True)