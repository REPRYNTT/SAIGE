import os
import json
import hashlib
from flask import Flask, request, jsonify, send_from_directory
import requests
from ecdsa import SigningKey, SECP256k1, VerifyingKey
from subprocess import Popen, PIPE, call  # For safe command execution
import pysbd  # Sentence splitter
import time  # For delay
import threading
import queue
from collections import deque

app = Flask(__name__, static_folder='static')

# Config
LLAMA_API = 'http://localhost:8080/v1/chat/completions'
LOG_FILE = 'logs/saige_chat.log'  # Local logs directory - no root required
BLOCKCHAIN_KEY_FILE = os.path.expanduser('~/.saige_signing_key.pem')  # Persistent key
INFERENCE_LOG = 'logs/saige_inference.log'  # Local logs directory - no root required

# Load or generate ECDSA key for blockchain-style signing
if not os.path.exists(BLOCKCHAIN_KEY_FILE):
    signing_key = SigningKey.generate(curve=SECP256k1)
    with open(BLOCKCHAIN_KEY_FILE, 'wb') as f:
        f.write(signing_key.to_pem())
else:
    with open(BLOCKCHAIN_KEY_FILE, 'rb') as f:
        signing_key = SigningKey.from_pem(f.read())
verifying_key = signing_key.verifying_key

# TTS Worker Class for Non-blocking Audio - Piper TTS (ARM64 Fixed)
class TTSWorker:
    def __init__(self):
        self.tts_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_tts, daemon=True)
        self.worker_thread.start()
        
        # Piper TTS configuration (ARM64/Jetson optimized)
        self.piper_model = os.path.expanduser("~/SAIGE/models/piper/en_US-lessac-medium.onnx")
        self.use_piper = os.path.exists(self.piper_model)
        
        if self.use_piper:
            print(f"[TTS] Using Piper TTS model: {self.piper_model}")
        else:
            print(f"[TTS] Piper model not found, falling back to Mimic3")
        
    def _process_tts(self):
        """Background thread that processes TTS queue without blocking"""
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
        """Synthesize and play audio - Piper TTS optimized for ARM64"""
        try:
            thread_id = threading.current_thread().ident
            temp_audio = f'/tmp/saige_tts_{thread_id}.wav'
            
            if self.use_piper:
                # Use Piper TTS (faster, MIT licensed, ARM64 compatible)
                with open(os.devnull, 'w') as devnull:
                    # Direct piper command with proper error handling
                    process = Popen([
                        'piper',
                        '--model', self.piper_model,
                        '--output_file', temp_audio
                    ], stdin=PIPE, stdout=devnull, stderr=devnull, text=True)
                    
                    # Send text to piper stdin
                    process.communicate(input=text)
                    
                    if process.returncode == 0 and os.path.exists(temp_audio):
                        # Play audio directly (no stereo conversion needed)
                        call(['aplay', '-D', 'hw:0,0', temp_audio], stderr=devnull)
                    
            else:
                # Fallback to Mimic3 (your current implementation)
                temp_mono = f'/tmp/tts_mono_{thread_id}.wav'
                temp_stereo = f'/tmp/tts_stereo_{thread_id}.wav'
                
                with open(os.devnull, 'w') as devnull:
                    call(['mimic3', '--voice', 'en_US/cmu-arctic_low', 
                         '--length-scale', '0.9', text], 
                         stdout=open(temp_mono, 'wb'), stderr=devnull)
                    
                    call(['sox', temp_mono, '-c', '2', temp_stereo], stderr=devnull)
                    call(['aplay', '-D', 'hw:0,0', temp_stereo], stderr=devnull)
                    
                    try:
                        os.remove(temp_mono)
                        os.remove(temp_stereo)
                    except:
                        pass
            
            # Cleanup
            try:
                os.remove(temp_audio)
            except:
                pass
                
        except Exception as e:
            print(f"TTS synthesis error: {e}")
    
    def add_text(self, text):
        """Add text to TTS queue - optimized for word-level streaming"""
        if text.strip():
            # For word-for-word streaming, reduce chunk size even more
            clean_text = text.strip()
            # Keep some punctuation for natural pauses (Piper handles this better)
            clean_text = clean_text.replace('  ', ' ')  # Just clean double spaces
            
            if clean_text:
                self.tts_queue.put(clean_text)

# Initialize TTS worker
tts_worker = TTSWorker()

def log_with_signature(message, response):
    log_entry = f"User: {message}\nAssistant: {response}\n"
    hash_digest = hashlib.sha256(log_entry.encode()).digest()
    signature = signing_key.sign(hash_digest).hex()
    with open(LOG_FILE, 'a') as f:
        f.write(f"{log_entry}Signature: {signature}\nBlock Hash: {hashlib.sha256(hash_digest + bytes.fromhex(signature)).hexdigest()}\n---\n")
    return signature

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    messages = data.get('messages', [])
    # Proxy to llama-server with streaming
    try:
        resp = requests.post(LLAMA_API, json={
            'messages': messages,
            'model': 'phi-3-mini',
            'stream': True,
            'max_tokens': 512,
            'temperature': 0.85
        }, stream=True)
        resp.raise_for_status()

        def generate():
            response_text = ''
            tts_buffer = ''
            word_count = 0
            
            for chunk in resp.iter_lines():
                if chunk:
                    line = chunk.decode('utf-8').strip()
                    if line.startswith('data: '):
                        if line[6:].strip() == '[DONE]':
                            # Send any remaining buffer to TTS
                            if tts_buffer.strip():
                                tts_worker.add_text(tts_buffer)
                            break
                            
                        try:
                            data = json.loads(line[6:])
                            if 'choices' in data and data['choices']:
                                content = data['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    response_text += content
                                    tts_buffer += content
                                    
                                    # Count words
                                    if ' ' in content:
                                        word_count += content.count(' ')
                                    
                                    # Send to TTS after fewer words with Piper (faster)
                                    if word_count >= 2:  # Ultra-fast - just 2 words with Piper!
                                        tts_worker.add_text(tts_buffer.strip())
                                        tts_buffer = ''  # Clear buffer
                                        word_count = 0
                                    
                                    # Yield content immediately to UI
                                    yield content
                        except json.JSONDecodeError:
                            continue
            
            # Log after full response
            user_msg = messages[-1]['content'] if messages else ''
            log_with_signature(user_msg, response_text)

        return app.response_class(generate(), mimetype='text/event-stream')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs', methods=['GET'])
def get_logs():
    try:
        with open(LOG_FILE, 'r') as f:
            logs = f.read()
        with open(INFERENCE_LOG, 'r') as f:
            inf_logs = f.read()
        return jsonify({'chat_logs': logs, 'inference_logs': inf_logs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/verify_blockchain', methods=['POST'])
def verify_blockchain():
    data = request.json
    log_entry = data.get('log_entry', '')
    signature = data.get('signature', '')
    try:
        hash_digest = hashlib.sha256(log_entry.encode()).digest()
        valid = verifying_key.verify(bytes.fromhex(signature), hash_digest)
        return jsonify({'valid': valid})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/command', methods=['POST'])
def run_command():
    data = request.json
    cmd = data.get('command', '')
    # Restrict to safe SAIGE commands (extend as needed for autonomy)
    allowed_cmds = {
        'evolve': 'cd ~/llama.cpp/build/bin && ./llama-evolve-binary --task "optimize for robotic autonomy"',  # Assume you build this C++ binary
        'status': 'jtop --json',
        'update': 'git -C ~/SAIGE pull'
    }
    if cmd in allowed_cmds:
        proc = Popen(allowed_cmds[cmd], shell=True, stdout=PIPE, stderr=PIPE)
        out, err = proc.communicate()
        return jsonify({'output': out.decode(), 'error': err.decode()})
    return jsonify({'error': 'Unauthorized command'}), 403

if __name__ == '__main__':
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    os.makedirs(os.path.dirname(INFERENCE_LOG), exist_ok=True)  # Create both log dirs
    app.run(host='0.0.0.0', port=5000, debug=False)  # Access from laptop at http://10.0.0.19:5000
