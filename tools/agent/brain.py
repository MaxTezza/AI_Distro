#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

# Paths
DEFAULT_MODEL_URL = "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf"
MODEL_DIR = Path(os.path.expanduser("~/.cache/ai-distro/models"))
MODEL_PATH = MODEL_DIR / "llama-3.2-1b-instruct.gguf"
SKILLS_DIR = Path(os.environ.get("AI_DISTRO_SKILLS_DIR", "src/skills/core"))

def load_skills():
    skills = []
    if not SKILLS_DIR.exists():
        return skills
    for p in SKILLS_DIR.glob("*.json"):
        try:
            with open(p, "r") as f:
                skills.append(json.load(f))
        except:
            pass
    return skills

def build_system_prompt(skills):
    prompt = "You are the AI Distro Assistant, a helpful and natural Linux assistant.
"
    prompt += "Your goal is to map user requests to structured JSON actions.

"
    prompt += "AVAILABLE ACTIONS:
"
    for s in skills:
        prompt += f"- {s['name']}: {s['description']}
"
        prompt += f"  Parameters: {json.dumps(s.get('parameters', {}))}
"
    
    prompt += "
INSTRUCTIONS:
"
    prompt += "1. Respond ONLY with a valid JSON object matching the ActionRequest format: {"version": 1, "name": "action_name", "payload": "parameter_value"}
"
    prompt += "2. If multiple parameters are needed, join them with '|' if the tool expects it, or use a comma-separated string for packages.
"
    prompt += "3. If no action matches, use {"name": "unknown", "payload": "..."}.
"
    prompt += "4. Be natural and conversational in your internal reasoning, but only output JSON.
"
    return prompt

def get_llama():
    try:
        from llama_cpp import Llama
        if not MODEL_PATH.exists():
            return None
        return Llama(model_path=str(MODEL_PATH), n_ctx=2048, verbose=False)
    except:
        return None

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"name": "unknown", "payload": "missing input"}))
        return

    user_input = " ".join(sys.argv[1:])
    skills = load_skills()
    
    llm = get_llama()
    if not llm:
        # Fallback to regex if LLM is not ready
        from intent_parser import main as regex_main
        # We'll just exit and let the agent call the old parser for now
        # to ensure we don't break things while downloading.
        sys.exit(1)

    system_prompt = build_system_prompt(skills)
    
    response = llm.create_chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        response_format={"type": "json_object"}
    )
    
    try:
        result = response["choices"][0]["message"]["content"]
        # Ensure it is valid JSON
        json.loads(result)
        print(result)
    except:
        print(json.dumps({"name": "unknown", "payload": user_input}))

if __name__ == "__main__":
    main()
