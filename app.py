import os
import uuid
import tempfile
import logging
from flask import Flask, render_template, request, jsonify, url_for
import whisper
import ollama
import pyttsx3

# --- CONFIGURATION ---
# PASTE YOUR VOICE ID HERE (Use the find_voices.py script from before if needed)
VOICE_ID = "com.apple.speech.synthesis.voice.ting-ting" # Example: Mac Chinese/English
# VOICE_ID = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0" # Example: Windows
# ---------------------

app = Flask(__name__)

# Ensure we have a folder for audio files
STATIC_AUDIO_DIR = os.path.join(os.getcwd(), 'static', 'audio')
os.makedirs(STATIC_AUDIO_DIR, exist_ok=True)

print("Loading Whisper...")
whisper_model = whisper.load_model("base")
print("✅ Whisper Ready")

@app.route('/')
def index():
    return render_template('index.html')

# --- ROUTE 1: TRANSCRIBE (Whisper) ---
@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio part'}), 400

    audio_file = request.files['audio']
    
    # Save temp file for Whisper
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        audio_file.save(temp.name)
        temp_path = temp.name

    try:
        # Transcribe
        result = whisper_model.transcribe(temp_path, fp16=False)
        text = result['text'].strip()
        return jsonify({'text': text})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- ROUTE 2: CHAT + TTS (Ollama + pyttsx3) ---
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_text = data.get('text')
    
    if not user_text:
        return jsonify({'error': 'No text provided'}), 400

    try:
        # 1. Get AI Response
        response = ollama.chat(model='llama3.2:3b', messages=[{'role': 'user', 'content': user_text}])
        ai_text = response['message']['content']

        # 2. Generate Audio (Offline TTS)
        # Create a unique filename so the browser doesn't cache the old "response.wav"
        filename = f"response_{uuid.uuid4().hex}.wav"
        save_path = os.path.join(STATIC_AUDIO_DIR, filename)

        # Initialize Engine (New instance per request is safer for Flask)
        engine = pyttsx3.init()
        try:
            engine.setProperty('voice', VOICE_ID)
        except:
            pass # Fallback to default if ID is wrong
        
        engine.setProperty('rate', 175) # Speed
        engine.save_to_file(ai_text, save_path)
        engine.runAndWait()

        # 3. Return Text and Audio URL
        audio_url = url_for('static', filename=f'audio/{filename}')
        
        return jsonify({
            'response': ai_text, 
            'audio_url': audio_url
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # SSL context required for Mobile Mic
    try:
        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')
    except:
        print("⚠️ SSL Failed. Mic might not work on mobile.")
        app.run(host='0.0.0.0', port=5000, debug=True)