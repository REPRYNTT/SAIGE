import requests
from flask import Flask, request, jsonify, render_template, Response
import json
import threading
import queue
import time
import os
import subprocess
from subprocess import call, Popen, PIPE
from ecdsa import SigningKey, NIST256p
import hashlib
import base64

app = Flask(__name__)

# Configuration
LLAMA_API = 'http://localhost:8080/v1/chat/completions'
BLOCKCHAIN_KEY_FILE = '/home/input_your_info_here/.ssh/saige_blockchain_key.pem'
BLOCKCHAIN_LOG_FILE = '/home/input_your_info_here/saige_blockchain.json'

# Generate or load blockchain key
if not os.path.exists(BLOCKCHAIN_KEY_FILE):
    os.makedirs(os.path.dirname(BLOCKCHAIN_KEY_FILE), exist_ok=True)
    signing_key = SigningKey.generate(curve=NIST256p)
    with open(BLOCKCHAIN_KEY_FILE, 'wb') as f:
        f.write(signing_key.to_pem())
else:
    with open(BLOCKCHAIN_KEY_FILE, 'rb') as f:
        signing_key = SigningKey.from_pem(f.read())
verifying_key = signing_key.verifying_key

# TTS Worker Class - Piper TTS with Natural Speech Flow
class TTSWorker:
    def __init__(self):
        self.tts_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_tts, daemon=True)
        self.worker_thread.start()

        # Piper TTS configuration
        self.piper_model = os.path.expanduser("~/SAIGE/models/piper/en_US-ryan-high.onnx")
        self.use_piper = os.path.exists(self.piper_model)

        if self.use_piper:
            print(f"[TTS] Using Piper TTS model: {self.piper_model}")
        else:
            print(f"[TTS] Piper model not found, falling back to Mimic3")

    def _process_tts(self):
        while True:
            try:
                sentence = self.tts_queue.get(timeout=1)
                if sentence:
                    self._synthesize_and_play(sentence)
                self.tts_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Error: {e}")

    def _synthesize_and_play(self, text):
        try:
            thread_id = threading.current_thread().ident
            temp_audio = f"/tmp/saige_tts_{thread_id}.wav"

            if self.use_piper:
                with open(os.devnull, "w") as devnull:
                    process = Popen([
                        "piper",
                        "--model", self.piper_model,
                        "--output_file", temp_audio
                    ], stdin=PIPE, stdout=devnull, stderr=devnull, text=True)

                    process.communicate(input=text)

                    if process.returncode == 0 and os.path.exists(temp_audio):
                        temp_stereo = f"/tmp/saige_tts_stereo_{thread_id}.wav"
                        call(["sox", temp_audio, "-c", "2", temp_stereo], stderr=devnull)
                        call(["aplay", "-D", "hw:0,0", temp_stereo], stderr=devnull)
                        
                        try:
                            os.remove(temp_stereo)
                            os.remove(temp_audio)
                        except:
                            pass
            else:
                # Fallback to Mimic3
                temp_mono = f"/tmp/tts_mono_{thread_id}.wav"
                temp_stereo = f"/tmp/tts_stereo_{thread_id}.wav"

                with open(os.devnull, "w") as devnull:
                    call(["mimic3", "--voice", "en_US/cmu-arctic_low",
                         "--length-scale", "0.9", text],
                         stdout=open(temp_mono, "wb"), stderr=devnull)

                    call(["sox", temp_mono, "-c", "2", temp_stereo], stderr=devnull)
                    call(["aplay", "-D", "hw:0,0", temp_stereo], stderr=devnull)

                    try:
                        os.remove(temp_mono)
                        os.remove(temp_stereo)
                    except:
                        pass

        except Exception as e:
            print(f"TTS synthesis error: {e}")

    def add_text(self, text):
        if text.strip():
            clean_text = text.strip().replace("  ", " ")
            if clean_text:
                self.tts_queue.put(clean_text)

# Initialize TTS worker
tts_worker = TTSWorker()

def log_with_signature(message, response):
    log_entry = f"User: {message}\nAssistant: {response}\n"
    message_hash = hashlib.sha256(log_entry.encode()).digest()
    signature = signing_key.sign(message_hash)
    
    blockchain_entry = {
        'timestamp': time.time(),
        'message': message,
        'response': response,
        'hash': base64.b64encode(message_hash).decode(),
        'signature': base64.b64encode(signature).decode()
    }
    
    with open(BLOCKCHAIN_LOG_FILE, 'a') as f:
        f.write(json.dumps(blockchain_entry) + '\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get('message', '')
    
    def generate():
        try:
            # Connect to your Phi-3 model via llama-server
            resp = requests.post(LLAMA_API, json={
                'messages': [{'role': 'user', 'content': user_message}],
                'model': 'phi-3-mini',
                'stream': True,
                'max_tokens': 512,
                'temperature': 0.85
            }, stream=True)
            resp.raise_for_status()
            
            sentence_buffer = ''
            response_text = ''
            
            for chunk in resp.iter_lines():
                if chunk:
                    line = chunk.decode('utf-8').strip()
                    if line.startswith('data: '):
                        if line[6:].strip() == '[DONE]':
                            # Handle final buffer
                            if sentence_buffer.strip():
                                tts_worker.add_text(sentence_buffer.strip())
                            break
                            
                        try:
                            data = json.loads(line[6:])
                            if 'choices' in data and data['choices']:
                                content = data['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    sentence_buffer += content
                                    response_text += content
                                    
                                    # Stream to UI immediately
                                    yield "data: " + json.dumps({'content': content}) + "\n\n"
                                    
                                    # Send complete sentences to TTS for natural flow
                                    is_sentence_end = content.rstrip().endswith(('.', '!', '?'))
                                    is_long_phrase = len(sentence_buffer.split()) >= 12
                                    
                                    if is_sentence_end or is_long_phrase:
                                        tts_worker.add_text(sentence_buffer.strip())
                                        sentence_buffer = ''
                                    
                                    time.sleep(0.05)
                        except json.JSONDecodeError:
                            continue
            
            # Log to blockchain
            log_with_signature(user_message, response_text)
            yield "data: " + json.dumps({'done': True}) + "\n\n"
            
        except Exception as e:
            error_msg = f"Error connecting to Phi-3 model: {e}. Make sure llama-server is running on port 8080."
            yield "data: " + json.dumps({'content': error_msg}) + "\n\n"
            yield "data: " + json.dumps({'done': True}) + "\n\n"
    
    return Response(generate(), mimetype='text/plain')

@app.route('/logs')
def get_logs():
    logs = []
    if os.path.exists(BLOCKCHAIN_LOG_FILE):
        with open(BLOCKCHAIN_LOG_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
    return jsonify(logs)

@app.route('/verify')
def verify_blockchain():
    if not os.path.exists(BLOCKCHAIN_LOG_FILE):
        return jsonify({'status': 'No blockchain file found'})
    
    verified_count = 0
    total_count = 0
    
    with open(BLOCKCHAIN_LOG_FILE, 'r') as f:
        for line in f:
            if line.strip():
                total_count += 1
                try:
                    entry = json.loads(line)
                    log_entry = f"User: {entry['message']}\nAssistant: {entry['response']}\n"
                    message_hash = hashlib.sha256(log_entry.encode()).digest()
                    
                    expected_hash = base64.b64decode(entry['hash'])
                    signature = base64.b64decode(entry['signature'])
                    
                    if message_hash == expected_hash and verifying_key.verify(signature, message_hash):
                        verified_count += 1
                except:
                    pass
    
    return jsonify({
        'total_entries': total_count,
        'verified_entries': verified_count,
        'integrity': f"{verified_count}/{total_count} verified"
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SAIGE - Self-Evolving AI with Real Phi-3 Integration")
    print("=" * 60)
    print(f"✅ AI Model: Phi-3 Mini via llama-server (localhost:8080)")
    print(f"✅ TTS Engine: {'Piper (MIT Licensed)' if tts_worker.use_piper else 'Mimic3 (Fallback)'}")
    print(f"✅ Audio Device: hw:0,0 (USB Audio)")
    print(f"✅ Speech Flow: Natural sentence-based streaming")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
