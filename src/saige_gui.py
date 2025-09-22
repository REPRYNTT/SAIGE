import os
import json
import hashlib
from flask import Flask, request, jsonify, send_from_directory
import requests
from ecdsa import SigningKey, SECP256k1, VerifyingKey
from subprocess import Popen, PIPE  # For safe command execution

app = Flask(__name__, static_folder='static')

# Config
LLAMA_API = 'http://localhost:8080/v1/chat/completions'
LOG_FILE = '/var/log/saige_chat.log'
BLOCKCHAIN_KEY_FILE = os.path.expanduser('~/.saige_signing_key.pem')  # Persistent key
INFERENCE_LOG = '/var/log/saige_inference.log'

# Load or generate ECDSA key for blockchain-style signing
if not os.path.exists(BLOCKCHAIN_KEY_FILE):
    signing_key = SigningKey.generate(curve=SECP256k1)
    with open(BLOCKCHAIN_KEY_FILE, 'wb') as f:
        f.write(signing_key.to_pem())
else:
    with open(BLOCKCHAIN_KEY_FILE, 'rb') as f:
        signing_key = SigningKey.from_pem(f.read())
verifying_key = signing_key.verifying_key

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
            for chunk in resp.iter_lines():
                if chunk:
                    line = chunk.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = json.loads(line[6:])
                        if 'choices' in data and data['choices']:
                            content = data['choices'][0].get('delta', {}).get('content', '')
                            response_text += content
                            yield content
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
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=False)  # Access from laptop at http://10.0.0.19:5000
