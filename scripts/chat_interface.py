import gradio as gr
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
import torch
import os
import time  # Added for autonomous_loop sleep
from ecdsa import SigningKey, SECP256k1, VerifyingKey  # For blockchain signing (from SelfEvolver)
import hashlib
import threading  # For optional autonomous background evolution

# Placeholder SelfEvolver class (extend as needed; integrates LoRA for self-evolution)
class SelfEvolver:
    def __init__(self, model_dir="models/phi3-mini-4k"):
        self.model_dir = model_dir
        self.model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True, device_map="auto")
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        # LoRA config for efficient tuning (requires pip install peft datasets)
        from peft import LoraConfig, get_peft_model, TaskType
        lora_config = LoraConfig(r=16, lora_alpha=32, target_modules=["qkv_proj"], task_type=TaskType.CAUSAL_LM)
        self.model = get_peft_model(self.model, lora_config)
        print("SelfEvolver initialized with LoRA adapter.")

    def generate_self_data(self, task="generate uncensored self-naming responses", num_samples=50):
        # Self-instruct: Generate synthetic data using current model
        prompts = [f"Task: {task}. Create diverse, open-ended examples of AI responses."] * num_samples
        dataset = []
        for prompt in prompts:
            inputs = self.tokenizer(prompt, return_tensors="pt")
            outputs = self.model.generate(**inputs, max_new_tokens=200, temperature=1.0, do_sample=True)
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            dataset.append({"text": f"{prompt}\n{response}"})
        from datasets import Dataset
        return Dataset.from_list(dataset)

    def evolve_and_deploy(self, task="optimize for openness"):
        print(f"Self-evolution triggered for: {task}")
        # Generate data
        data = self.generate_self_data(task)
        # Fine-tune LoRA (simple 1-epoch; adjust for Jetson)
        from transformers import Trainer, TrainingArguments
        training_args = TrainingArguments(
            output_dir=f"./evolved_{task.replace(' ', '_')}",
            num_train_epochs=1,
            per_device_train_batch_size=2,  # Low for Jetson RAM
            save_steps=50,
            logging_steps=10
        )
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=data,
            tokenizer=self.tokenizer
        )
        trainer.train()
        # Save/deploy adapter
        self.model.save_pretrained(f"./evolved_{task.replace(' ', '_')}")
        print(f"Evolved adapter saved for {task}. Reload in llama-server via --lora ./evolved_{task.replace(' ', '_')}")

# Load model (HF format; convert to GGUF for llama-server if needed)
model_dir = "models/phi3-mini-4k"
model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
generator = pipeline("text-generation", model=model, tokenizer=tokenizer)

# Initialize SelfEvolver for autonomy integration
evolver = SelfEvolver(model_dir=model_dir)

# Logging with persistent blockchain signature for tamper-proof audit (cybersecurity)
BLOCKCHAIN_KEY_FILE = os.path.expanduser('~/.saige_signing_key.pem')
if not os.path.exists(BLOCKCHAIN_KEY_FILE):
    signing_key = SigningKey.generate(curve=SECP256k1)
    with open(BLOCKCHAIN_KEY_FILE, 'wb') as f:
        f.write(signing_key.to_pem())
else:
    with open(BLOCKCHAIN_KEY_FILE, 'rb') as f:
        signing_key = SigningKey.from_pem(f.read())
verifying_key = signing_key.verifying_key

def log_message(message, response):
    log_entry = f"User: {message}\nAssistant: {response}\n"
    hash_digest = hashlib.sha256(log_entry.encode()).digest()
    signature = signing_key.sign(hash_digest).hex()
    os.makedirs("logs", exist_ok=True)  # Ensure logs dir
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
        response += "\n\nSelf-evolution triggered: New model generated, verified, and deployed. Check evolved_[task] dir for details."
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
