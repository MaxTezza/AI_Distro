#!/usr/bin/env python3
import os
import requests
from pathlib import Path
from tqdm import tqdm

MODEL_URL = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_DIR = Path(os.path.expanduser("~/.cache/ai-distro/models"))
MODEL_PATH = MODEL_DIR / "llama-3.2-1b-instruct.gguf"

def download_model():
    if MODEL_PATH.exists():
        print(f"Model already exists at {MODEL_PATH}")
        return

    print(f"Downloading Local LLM Brain (Llama 3.2 1B)...")
    print("This only happens once. No API keys required.")
    
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    response = requests.get(MODEL_URL, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(MODEL_PATH, "wb") as f, tqdm(
        desc="Downloading",
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)

    print(f"
Success! Brain initialized at {MODEL_PATH}")

if __name__ == "__main__":
    download_model()
