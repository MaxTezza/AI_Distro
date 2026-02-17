#!/usr/bin/env python3
import time
import speech_recognition as sr
import subprocess
import os
import sys
import logging
import json

# Configuration
WAKE_WORD = "computer"
BRAIN_SCRIPT = os.path.join(os.path.dirname(__file__), "brain.py")
AGENT_SOCKET = os.environ.get("AI_DISTRO_IPC_SOCKET", "/tmp/ai-distro-agent.sock")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def speak(text):
    """Speak using espeak CLI for maximum compatibility"""
    logging.info(f"Speaking: {text}")
    try:
        subprocess.run(["espeak", "-v", "en-us", "-s", "160", text], check=False)
    except Exception as e:
        logging.error(f"TTS failed: {e}")

def call_agent_ipc(action_json):
    """Send JSON action to Rust agent via Unix Socket"""
    import socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.connect(AGENT_SOCKET)
            client.sendall(action_json.encode('utf-8') + b"\n")
            response = client.recv(4096).decode('utf-8')
            return json.loads(response)
    except Exception as e:
        logging.error(f"IPC Error: {e}")
        return None

def process_command(text):
    logging.info(f"Command text: {text}")
    try:
        # 1. Get Intent from Brain
        res = subprocess.run(
            [sys.executable, BRAIN_SCRIPT, text],
            capture_output=True, text=True, timeout=12
        )
        
        if res.returncode != 0:
            speak("I had trouble thinking about that.")
            return

        intent_json = res.stdout.strip()
        logging.info(f"Intent: {intent_json}")
        
        # 2. Execute via Agent IPC
        speak("Working on it.")
        outcome = call_agent_ipc(intent_json)
        
        if outcome and outcome.get("status") == "ok":
            msg = outcome.get("message", "Done.")
            speak(msg)
        elif outcome and outcome.get("status") == "deny":
            speak("I'm not allowed to do that.")
        else:
            speak("I couldn't finish that task.")

    except Exception as e:
        logging.error(f"Process Error: {e}")
        speak("Something went wrong.")

def listen_loop():
    r = sr.Recognizer()
    mic = sr.Microphone()
    
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=1)
        logging.info("Listening for wake word...")

    while True:
        try:
            with mic as source:
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
            
            text = r.recognize_google(audio).lower()
            logging.info(f"Heard: {text}")

            if WAKE_WORD in text:
                # Extract command after wake word
                parts = text.split(WAKE_WORD, 1)
                cmd = parts[1].strip()
                if cmd:
                    process_command(cmd)
                else:
                    speak("Yes?")
        
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            logging.error(f"Loop Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    if not os.path.exists(BRAIN_SCRIPT):
        logging.error("brain.py not found!")
        sys.exit(1)
        
    speak("Voice control ready.")
    listen_loop()
