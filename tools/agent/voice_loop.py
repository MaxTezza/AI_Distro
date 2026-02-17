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
    """Direct Voice Output"""
    logging.info(f"Speaking: {text}")
    try:
        subprocess.run(["espeak", "-v", "en-us+f2", "-s", "170", text], check=False)
    except Exception as e:
        logging.error(f"TTS failed: {e}")

def call_agent_ipc(action_json):
    """Direct IPC Call"""
    import socket
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(15.0)
            client.connect(AGENT_SOCKET)
            client.sendall(action_json.encode('utf-8') + b"\n")
            response = client.recv(8192).decode('utf-8')
            return json.loads(response)
    except Exception as e:
        logging.error(f"IPC Error: {e}")
        return None

def process_command(text):
    """Direct Command Execution"""
    logging.info(f"Command: {text}")
    try:
        # 1. Intent Parsing
        res = subprocess.run(
            [sys.executable, BRAIN_SCRIPT, text],
            capture_output=True, text=True, timeout=12
        )
        
        if res.returncode != 0:
            return

        intent_json = res.stdout.strip()
        
        # 2. Immediate Execution & Response
        outcome = call_agent_ipc(intent_json)
        
        if outcome:
            # Speak the actual content returned by the tool (e.g. Day Planner advice)
            msg = outcome.get("message", "")
            if msg:
                speak(msg)
        else:
            speak("Interface error.")

    except Exception as e:
        logging.error(f"Process Error: {e}")

def listen_loop():
    r = sr.Recognizer()
    mic = sr.Microphone()
    
    with mic as source:
        r.adjust_for_ambient_noise(source, duration=1)
        logging.info("System Ready.")

    while True:
        try:
            with mic as source:
                audio = r.listen(source, timeout=5, phrase_time_limit=8)
            
            text = r.recognize_google(audio).lower()
            logging.info(f"Input: {text}")

            if WAKE_WORD in text:
                cmd = text.split(WAKE_WORD, 1)[1].strip()
                if cmd:
                    process_command(cmd)
        
        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            time.sleep(1)

if __name__ == "__main__":
    if not os.path.exists(BRAIN_SCRIPT):
        sys.exit(1)
    listen_loop()
