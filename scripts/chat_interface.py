import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import os
from ecdsa import SigningKey, SECP256k1, VerifyingKey  # For blockchain signing (from SelfEvolver)
import hashlib
import threading  # For optional autonomous background evolution
from self_evolve import SelfEvolver  # Import your SelfEvolver class

model_dir = "models/phi3-mini-4k"
model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)

generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

# Initialize SelfEvolver for autonomy integration
evolver = SelfEvolver(model_dir=model_dir)

# Logging with blockchain signature for tamper-proof audit (cybersecurity)
signing_key = SigningKey.generate(curve=SECP256k1)
verifying_key = signing_key.verifying_key

def log_message(message, response):
    log_entry = f"User: {message}\nAssistant: {response}\n"
    signature = signing_key.sign(hashlib.sha256(log_entry.encode()).digest()).hex()
    with open("logs/chat_log.txt", "a") as f:
        f.write(f"{log_entry}Signature: {signature}\n---\n")

def generate_response(message, history):
    # Build prompt with history for context-aware self-thinking
    prompt = ""
    for user_msg, bot_msg in history:
        prompt += f"User: {user_msg}\nAssistant: {bot_msg}\n"
    prompt += f"User: {message}\nAssistant:"
    
    # Generate response with unrestricted discourse
    output = generator(prompt, max_new_tokens=250, do_sample=True, temperature=0.85, num_return_sequences=1)
    response = output[0]['generated_text'].split("Assistant:")[-1].strip()
    
    # Autonomy trigger: If "evolve" in message, initiate self-evolution
    if "evolve" in message.lower():
        task = message.replace("evolve", "").strip() or "optimize for robotic autonomy"
        evolver.evolve_and_deploy(task)
        response += "\n\nSelf-evolution triggered: New model generated, verified, and deployed. Check generated_model.py for details."
    
    # Log with signature
    log_message(message, response)
    
    return response

# Optional: Background thread for periodic autonomous evolution (headless mode for production)
def autonomous_loop():
    while True:
        evolver.evolve_and_deploy("enhance self-thinking capabilities")
        time.sleep(3600)  # Evolve hourly; adjust for production

# Uncomment for autonomous background ops: threading.Thread(target=autonomous_loop, daemon=True).start()

demo = gr.ChatInterface(
    fn=generate_response,
    title="SAIGE Phi-3 Mini Chat: Self-Autonomous AI Prototype",
    description="Interact with the self-thinking AI on Jetson Orin Nano Super. Use 'evolve [task]' to trigger autonomous model creation (e.g., 'evolve robotic pathfinder').",
    examples=["Tell me about self-evolving AI.", "Evolve a neural net for decision-making."]
)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)  # share=False for cybersecurity; local network access only
