import os
from transformers import AutoModelForCausalLM, AutoTokenizer

model_dir = "models/phi3-mini-4k"
os.makedirs(model_dir, exist_ok=True)

model_name = "microsoft/Phi-3-mini-4k-instruct"
model = AutoModelForCausalLM.from_pretrained(model_name, trust_remote_code=True)
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

model.save_pretrained(model_dir)
tokenizer.save_pretrained(model_dir)

print(f"Phi-3 Mini 4K Instruct saved to: {model_dir}")
