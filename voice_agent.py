"""
Local Voice-Controlled Intelligent Agent
Offline task automation using Whisper (STT), Ollama (optional LLM), pyttsx3 (TTS),
pyautogui, OCR, and system automation. Works fully offline when Ollama is running locally.
"""

from __future__ import annotations

import json
import os
import random
import re
import shutil
import subprocess
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
import time
import winreg
from datetime import datetime
from pathlib import Path

import pyautogui
import pyttsx3
import sounddevice as sd
import whisper
import numpy as np
from scipy import signal
from scipy.io.wavfile import write

# Optional: Windows volume control
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    _PYCAW_AVAILABLE = True
except Exception:
    _PYCAW_AVAILABLE = False

# Optional: OCR for read screen
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageOps
    _OCR_AVAILABLE = True
except Exception:
    _OCR_AVAILABLE = False
    Image = None  # type: ignore

# Optional: Ollama
try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    _REQUESTS_AVAILABLE = False

# Optional: clipboard for typing any text
try:
    import pyperclip
    _PYPERCLIP_AVAILABLE = True
except Exception:
    _PYPERCLIP_AVAILABLE = False


# --------------- Config ---------------
CONFIG_PATH = Path(__file__).parent / "config.json"
DEFAULT_CONFIG = {
    "wake_word": "nova",
    "ollama": {"url": "http://localhost:11434/api/generate", "model": "llama3:latest", "timeout_seconds": 20},
    "audio": {
        "sample_rate": 16000,
        "duration_seconds": 5,
        "command_file": "command.wav",
        "device_id": None,
        "preprocess_audio": True,
        "noise_profile_seconds": 0.35,
        "noise_gate_multiplier": 2.0,
        "highpass_hz": 85,
        "calibrated_noise_floor": None,
        "calibrated_at": None,
        "auto_calibrate_on_startup": False,
        "auto_calibrate_seconds": 2.0,
    },
    "paths": {
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "edge": r"C:\Program Files (x86)\Microsoft Edge\Application\msedge.exe",
        "tesseract": r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    },
    "whisper_model": "small",
    "use_ollama": True,
    "confirm_chrome": False,
    "use_keyword_catch": True,
    "keyword_min_length": 2,
    "api": {
        "gemini_api_key": 'AIzaSyBOWXxubL4MnnDff6tx9mThURcz0y0WKR4',
        "use_gemini_llm": False,
        "gemini_model": "gemini-1.5-flash",
        "gemini_timeout_seconds": 30,
    },
    # Voice shortcuts: name -> https URL or Windows path to .exe/file (for internal tools / portals)
    "app_shortcuts": {
        "chatgpt": "https://chatgpt.com",
        "teams": "https://teams.microsoft.com",
        "outlook": "https://outlook.office.com",
    },
}

# Shared prompt for intent extraction (Ollama + OpenAI)
INTENT_SYSTEM_PROMPT = """You are a strict computer voice control agent. Reply with ONLY one action line, nothing else.

Allowed actions (return exactly one line):
- open notepad / open chrome / open edge / open files / open calculator
- open chatgpt
- open app <any installed app name, e.g. whatsapp, vlc, excel, teams>
- open task manager / open settings / open cmd / open powershell / open paint / open sticky notes
- open desktop / open documents / open downloads
- google search <query> / youtube search <query> / open url <url>
- whatsapp message <contact> | <message>
- scroll up / scroll down / scroll left / scroll right
- click center / move mouse left / move mouse right / move mouse up / move mouse down
- double click / right click
- type text <the exact text to type>
- press key <key> / press keys <key1> <key2>45
- copy text <phrase visible on screen to find and put on clipboard>
- copy / paste / cut / select all / undo / redo
- read screen / take screenshot / read clipboard
- close window / minimize window / maximize window
- snap window left / snap window right / show desktop / task view / next window
- refresh / go back / go forward / new tab / close tab
- volume up / volume down / mute volume / unmute volume
- play pause / next track / previous track
- lock computer / sleep / shutdown / restart
- what time / what date
- calibrate mic / calibration status / reset calibration
- repeat last action / do nothing / greet / appreciate
- run command <the exact command>
- create file <filename> / delete file <filename> / create folder <foldername> / delete folder <foldername>

Rules:
- if the user says hello, hi, hey, or greets you, return: greet (only for actual greetings, not praise)
- if the user expresses appreciation, praise, or says thanks (e.g., "you are awesome", "good job", "great work", "nice", "thank you"), return: appreciate
- For "type text X" return the exact text the user wants typed, in one line.
- For "copy the words …" or "copy text …" return one line: copy text <the phrase to find on screen>.
- For "press key X" use a single key name. For key combos use "press keys control c".
- If the user explicitly asks to run a system command or execute a terminal command, output ONE line: run command <the exact windows shell/powershell command>.
- For file/folder creation and deletion, extract the exact name and extension requested (e.g. "delete file script.py", "create folder photos").
- If user says "open whatsapp [name] ko message bhejo [message]", return: whatsapp message <name> | <message>
- If user says "youtube pe [query] dhundo", return: youtube search <query>
- If unclear or silence, return: do nothing. No explanations. Only the single action line."""

# Keyword catch: (list of keywords that must ALL appear in transcript, action).
# Order matters: more specific phrases first. Single-word triggers work even if rest is gibberish.
KEYWORD_ACTIONS = [
    # Two-word (more specific first)
    (["you", "are", "awesome"], "appreciate"),
    (["good", "job"], "appreciate"),
    (["great", "work"], "appreciate"),
    (["thank", "you"], "appreciate"),
    (["youtube", "search"], "youtube search"),  # query extracted in rule_based or we use last_query
    (["scroll", "down"], "scroll down"),
    (["scroll", "up"], "scroll up"),
    (["volume", "up"], "volume up"),
    (["volume", "down"], "volume down"),
    (["mouse", "left"], "move mouse left"),
    (["mouse", "right"], "move mouse right"),
    (["move", "left"], "move mouse left"),
    (["move", "right"], "move mouse right"),
    (["double", "click"], "double click"),
    (["right", "click"], "right click"),
    (["click", "center"], "click center"),
    (["close", "window"], "close window"),
    (["minimize", "window"], "minimize window"),
    (["maximize", "window"], "maximize window"),
    (["read", "screen"], "read screen"),
    (["take", "screenshot"], "take screenshot"),
    (["repeat", "last"], "repeat last action"),
    (["repeat", "again"], "repeat last action"),
    (["open", "notepad"], "open notepad"),
    (["open", "chrome"], "open chrome"),
    (["open", "edge"], "open edge"),
    (["open", "files"], "open files"),
    (["open", "calculator"], "open0 calculator"),
    (["open", "task", "manager"], "open task manager"),
    (["open", "settings"], "open settings"),
    (["open", "cmd"], "open cmd"),
    (["open", "powershell"], "open powershell"),
    (["open", "paint"], "open paint"),
    (["open", "desktop"], "open desktop"),
    (["open", "documents"], "open documents"),
    (["open", "downloads"], "open downloads"),
    (["open", "chatgpt"], "open chatgpt"),
    (["open", "chat", "gpt"], "open chatgpt"),
    (["scroll", "left"], "scroll left"),
    (["scroll", "right"], "scroll right"),
    (["move", "mouse", "up"], "move mouse up"),
    (["move", "mouse", "down"], "move mouse down"),
    (["snap", "left"], "snap window left"),
    (["snap", "right"], "snap window right"),
    (["show", "desktop"], "show desktop"),
    (["task", "view"], "task view"),
    (["next", "window"], "next window"),
    (["read", "clipboard"], "read clipboard"),
    (["what", "time"], "what time"),
    (["what", "date"], "what date"),
    (["calibrate", "mic"], "calibrate mic"),
    (["calibration", "status"], "calibration status"),
    (["reset", "calibration"], "reset calibration"),
    (["lock", "computer"], "lock computer"),
    (["play", "pause"], "play pause"),
    (["next", "track"], "next track"),
    (["previous", "track"], "previous track"),
    # Single keywords / mishearings (any one of these in transcript triggers)
    (["hello"], "greet"),
    (["hi"], "greet"),
    (["hey"], "greet"),
    (["greetings"], "greet"),
    (["thanks"], "appreciate"),
    (["appreciate"], "appreciate"),
    (["amazing"], "appreciate"),
    (["awesome"], "appreciate"),
    (["nice"], "appreciate"),
    (["notepad"], "open notepad"),
    (["note", "pad"], "open notepad"),
    (["chrome"], "open chrome"),
    (["edge"], "open edge"),
    (["calculator"], "open calculator"),
    (["calc"], "open calculator"),
    (["files"], "open files"),
    (["explorer"], "open files"),
    (["scroll"], "scroll down"),  # single "scroll" -> scroll down
    (["down"], "scroll down"),
    (["up"], "scroll up"),
    (["center"], "click center"),
    (["click"], "click center"),
    (["doubleclick"], "double click"),
    (["rightclick"], "right click"),
    (["close"], "close window"),
    (["minimize"], "minimize window"),
    (["maximize"], "maximize window"),
    (["screenshot"], "take screenshot"),
    (["capture"], "take screenshot"),
    (["screen"], "read screen"),
    (["read"], "read screen"),
    (["mute"], "mute volume"),
    (["unmute"], "unmute volume"),
    (["volume"], "volume up"),  # single "volume" -> volume up
    (["repeat"], "repeat last action"),
    (["again"], "repeat last action"),
    (["task", "manager"], "open task manager"),
    (["settings"], "open settings"),
    (["cmd"], "open cmd"),
    (["command", "prompt"], "open cmd"),
    (["powershell"], "open powershell"),
    (["paint"], "open paint"),
    (["sticky", "notes"], "open sticky notes"),
    (["desktop"], "open desktop"),
    (["documents"], "open documents"),
    (["downloads"], "open downloads"),
    (["copy"], "copy"),
    (["paste"], "paste"),
    (["cut"], "cut"),
    (["select", "all"], "select all"),
    (["undo"], "undo"),
    (["redo"], "redo"),
    (["clipboard"], "read clipboard"),
    (["time"], "what time"),
    (["date"], "what date"),
    (["calibrate"], "calibrate mic"),
    (["calibration"], "calibration status"),
    (["lock"], "lock computer"),
    (["sleep"], "sleep"),
    (["shutdown"], "shutdown"),
    (["restart"], "restart"),
    (["snap", "left"], "snap window left"),
    (["snap", "right"], "snap window right"),
    (["refresh"], "refresh"),
    (["back"], "go back"),
    (["forward"], "go forward"),
    (["new", "tab"], "new tab"),
    (["close", "tab"], "close tab"),
    (["play"], "play pause"),
    (["pause"], "play pause"),
    (["next"], "next track"),
    (["previous"], "previous track"),
]


def get_desktop_path() -> str:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        path, _ = winreg.QueryValueEx(key, "Desktop")
        return os.path.expandvars(path)
    except Exception:
        return os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Deep merge with defaults for missing keys
        for k, v in DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
            elif isinstance(v, dict) and isinstance(cfg.get(k), dict):
                for kk, vv in v.items():
                    if kk not in cfg[k]:
                        cfg[k][kk] = vv
        return cfg
    return DEFAULT_CONFIG.copy()


config = load_config()
WAKE_WORD = config["wake_word"].lower().strip()
STOP_WAKE_WORD = config.get("stop_wake_word", f"stop {WAKE_WORD}").lower().strip()
AUDIO_FILE = config["audio"].get("command_file", "command.wav")
SAMPLE_RATE = int(config["audio"].get("sample_rate", 16000))
DURATION = float(config["audio"].get("duration_seconds", 5))
DEVICE_ID = config["audio"].get("device_id")
PREPROCESS_AUDIO = bool(config["audio"].get("preprocess_audio", True))
NOISE_PROFILE_SECONDS = float(config["audio"].get("noise_profile_seconds", 0.35))
NOISE_GATE_MULTIPLIER = float(config["audio"].get("noise_gate_multiplier", 2.0))
HIGHPASS_HZ = float(config["audio"].get("highpass_hz", 85))
CALIBRATED_NOISE_FLOOR = config["audio"].get("calibrated_noise_floor")
CALIBRATED_AT = config["audio"].get("calibrated_at")
AUTO_CALIBRATE_ON_STARTUP = bool(config["audio"].get("auto_calibrate_on_startup", False))
AUTO_CALIBRATE_SECONDS = float(config["audio"].get("auto_calibrate_seconds", 2.0))
OLLAMA_URL = config["ollama"].get("url")
OLLAMA_MODEL = config["ollama"].get("model")
OLLAMA_TIMEOUT = int(config["ollama"].get("timeout_seconds", 20))
USE_OLLAMA = config.get("use_ollama", True)
CONFIRM_CHROME = config.get("confirm_chrome", False)
USE_KEYWORD_CATCH = config.get("use_keyword_catch", True)
KEYWORD_MIN_LEN = max(1, int(config.get("keyword_min_length", 2)))  # min transcript length to try keyword catch
PATH_CHROME = config["paths"].get("chrome")
PATH_EDGE = config["paths"].get("edge")
PATH_TESSERACT = config["paths"].get("tesseract")
WHISPER_MODEL_NAME = config.get("whisper_model", "base")

# Optional Gemini API (better understanding)
_api_cfg = config.get("api") or {}
GEMINI_API_KEY = _api_cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
GEMINI_API_KEY = (GEMINI_API_KEY or "").strip() or None
USE_GEMINI_LLM = bool(GEMINI_API_KEY and _api_cfg.get("use_gemini_llm", False))
GEMINI_MODEL = _api_cfg.get("gemini_model", "gemini-1.5-flash")
GEMINI_TIMEOUT = int(_api_cfg.get("gemini_timeout_seconds", 30))

# Global state for repeat last action
last_action = None
last_query = None

# Audio control globals
TTS_VOLUME = 0.8
MIC_SENSITIVITY = 0.4
IS_MUTED = False

# Lazy-loaded globals
_engine = None
_model = None
_volume_interface = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
    _engine.setProperty('volume', 0.0 if IS_MUTED else TTS_VOLUME)
    return _engine


def get_whisper_model():
    global _model
    if _model is None:
        _model = whisper.load_model(WHISPER_MODEL_NAME)
    return _model


def get_volume_interface():
    global _volume_interface
    if not _PYCAW_AVAILABLE or _volume_interface is not None:
        return _volume_interface
    try:
        devices = AudioUtilities.GetSpeakers()
        _volume_interface = devices.EndpointVolume
        return _volume_interface
    except Exception:
        return None


# --------------- Audio ---------------
def save_config():
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def calibrate_microphone(seconds: float = 2.0) -> str:
    """
    Capture ambient room sound (no speaking) and store calibrated noise floor.
    """
    global CALIBRATED_NOISE_FLOOR, CALIBRATED_AT
    kwargs = {"samplerate": SAMPLE_RATE, "channels": 1}
    if DEVICE_ID is not None:
        kwargs["device"] = DEVICE_ID
    n = max(1, int(seconds * SAMPLE_RATE))
    print("🔧 Calibrating mic... stay silent.")
    audio = sd.rec(n, **kwargs)
    sd.wait()
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    if x.size == 0:
        return "Calibration failed"
    x = x - np.mean(x)
    noise_floor = float(np.sqrt(np.mean(x**2)))
    CALIBRATED_NOISE_FLOOR = noise_floor
    CALIBRATED_AT = datetime.now().isoformat(timespec="seconds")
    config.setdefault("audio", {})
    config["audio"]["calibrated_noise_floor"] = CALIBRATED_NOISE_FLOOR
    config["audio"]["calibrated_at"] = CALIBRATED_AT
    save_config()
    return f"Mic calibrated. Noise floor {noise_floor:.5f}"


def preprocess_audio(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """
    Light-weight denoise pipeline for better STT without increasing record time:
    1) remove DC offset, 2) high-pass filter, 3) adaptive noise gate, 4) normalize.
    """
    x = np.asarray(audio, dtype=np.float32).reshape(-1)
    if x.size == 0:
        return np.zeros((0, 1), dtype=np.float32)

    # Remove DC offset
    x = x - np.mean(x)

    # High-pass filter (keep speech, suppress low-frequency hum/rumble)
    hp = max(20.0, min(HIGHPASS_HZ, (sample_rate / 2.0) - 100.0))
    if hp > 20:
        b, a = signal.butter(2, hp / (sample_rate / 2.0), btype="highpass")
        x = signal.lfilter(b, a, x).astype(np.float32)

    # Estimate noise floor from initial slice
    noise_n = max(1, min(int(NOISE_PROFILE_SECONDS * sample_rate), x.size))
    noise_slice = x[:noise_n]
    measured_noise = float(np.sqrt(np.mean(noise_slice**2)))
    calibrated = float(CALIBRATED_NOISE_FLOOR) if CALIBRATED_NOISE_FLOOR is not None else 0.0
    if calibrated > 0:
        noise_floor = min(measured_noise, calibrated * 2.0)
        noise_floor = max(noise_floor, calibrated)
    else:
        noise_floor = measured_noise
    
    noise_floor = max(noise_floor, 1e-6)

    # Normalize to stable amplitude for recognizer
    peak = float(np.max(np.abs(x)))
    # For quiet mics, we normalize if peak is just 1.5x the noise floor
    if peak > noise_floor * 1.5:
        x = np.clip((x / peak) * 0.95, -1.0, 1.0)

    return x.reshape(-1, 1).astype(np.float32)


def record_audio(prompt="🎤 Speak now..."):
    kwargs = {"samplerate": SAMPLE_RATE, "channels": 1}
    if DEVICE_ID is not None:
        kwargs["device"] = DEVICE_ID
    print(prompt)
    audio = sd.rec(int(DURATION * SAMPLE_RATE), **kwargs)
    sd.wait()
    if PREPROCESS_AUDIO:
        audio = preprocess_audio(audio, SAMPLE_RATE)
    write(AUDIO_FILE, SAMPLE_RATE, audio)


def speech_to_text():
    """Transcribe audio with local Whisper."""
    m = get_whisper_model()
    # Proper tuning to reduce noise hallucinations
    result = m.transcribe(
        AUDIO_FILE,
        language="en",
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        logprob_threshold=-1.0,
        temperature=0.0
    )
    text = (result.get("text") or "").lower().strip()
    print("🗣 You said:", text)
    return text


# --------------- LLM: Ollama (local) + Gemini (cloud, optional) ---------------
def ask_gemini_llm(user_text: str) -> str:
    """Use Gemini API for intent extraction when API key is set."""
    if not _REQUESTS_AVAILABLE or not USE_GEMINI_LLM or not GEMINI_API_KEY:
        return ""
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [
                    {
                        "parts": [
                            {
                                "text": (
                                    f"{INTENT_SYSTEM_PROMPT}\n\n"
                                    f"User command: {user_text}\n\n"
                                    "Return only the single action line."
                                )
                            }
                        ]
                    }
                ],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 120},
            },
            timeout=GEMINI_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        candidates = data.get("candidates") or []
        out = ""
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                out = (parts[0].get("text") or "").lower().strip()
        out = out.split("\n")[0].strip()
        return out
    except Exception as e:
        print("⚠️ Gemini LLM error:", e)
        return ""


def ask_ollama(user_text: str) -> str:
    if not _REQUESTS_AVAILABLE or not USE_OLLAMA:
        return ""
    full_prompt = f"{INTENT_SYSTEM_PROMPT}\n\nUser command: {user_text}\n\nAction:"
    try:
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": full_prompt, "stream": False},
            timeout=OLLAMA_TIMEOUT,
        )
        data = r.json()
        out = (data.get("response") or "").lower().strip()
        out = out.split("\n")[0].strip()
        return out
    except Exception as e:
        print("⚠️ Ollama error:", e)
        return ""

#################################################################################
#-----------------------dynamic code for asking llm-----------------------------#
#################################################################################


def ask_llm_for_dynamic_code(user_text: str) -> str:
    """
    Ask LLM to generate Python code for commands not in the hardcoded list.
    Returns executable Python code string or empty string if failed.
    """
    prompt = f"""You are a Windows computer automation expert.
The user gave this voice command: "{user_text}"

Write a single Python code snippet to fulfill this on Windows.
You can use: pyautogui, subprocess, os, time, webbrowser, keyboard shortcuts.

Rules:
- Return ONLY executable Python code, nothing else
- No markdown, no backticks, no explanation
- No imports needed, all libraries are already available
- Keep it short, max 5 lines
- If you truly cannot do it, return exactly: CANNOT_DO

Examples:
User: open spotify
Code: subprocess.Popen(['cmd', '/c', 'start', 'spotify:'])

User: move mouse to top right corner
Code: pyautogui.moveTo(pyautogui.size()[0] - 10, 10, duration=0.5)

User: type my name is nova
Code: pyperclip.copy('my name is nova'); pyautogui.hotkey('ctrl', 'v')
"""

    # Try Gemini first
    if USE_GEMINI_LLM and GEMINI_API_KEY and _REQUESTS_AVAILABLE:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200},
                },
                timeout=GEMINI_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    code = (parts[0].get("text") or "").strip()
                    # Clean markdown if LLM adds it anyway
                    code = re.sub(r"```python|```", "", code).strip()
                    return code
        except Exception as e:
            print("⚠️ Gemini dynamic code error:", e)

    # Try Ollama fallback
    if USE_OLLAMA and _REQUESTS_AVAILABLE:
        try:
            r = requests.post(
                OLLAMA_URL,
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=OLLAMA_TIMEOUT,
            )
            data = r.json()
            code = (data.get("response") or "").strip()
            code = re.sub(r"```python|```", "", code).strip()
            return code
        except Exception as e:
            print("⚠️ Ollama dynamic code error:", e)

    return ""


def execute_dynamic_code(code: str, user_text: str) -> str:
    """
    Safely execute LLM-generated code with voice confirmation first.
    """
    if not code or code.strip() == "CANNOT_DO":
        return "I don't know how to do that yet"

    # Sanitiy check — block dangerous commands
    blocked = ["rmdir", "del ", "format ", "shutil.rmtree", "os.remove",
               "shutdown", "registry", "regedit", "sys.exit", "__import__"]
    code_lower = code.lower()
    for danger in blocked:
        if danger in code_lower:
            return f"I blocked that command for safety — it contains '{danger}'"

    # Voice confirmation before executing
    preview = code[:80] + ("..." if len(code) > 80 else "")
    print(f"🤖 Dynamic code to run:\n{code}\n")
    get_engine().say(f"Should I run this? {user_text}")
    get_engine().runAndWait()

    record_audio("🎤 Say yes to confirm or no to cancel...")
    confirmation = speech_to_text()

    if "yes" in confirmation or "confirm" in confirmation or "do it" in confirmation:
        try:
            # Safe execution context — only expose needed libraries
            exec_globals = {
                "pyautogui": pyautogui,
                "subprocess": subprocess,
                "os": os,
                "time": time,
                "re": re,
                "pyperclip": pyperclip if _PYPERCLIP_AVAILABLE else None,
                "webbrowser": __import__("webbrowser"),
                "Path": Path,
            }
            exec(code, exec_globals)
            return f"Done: {user_text}"
        except Exception as e:
            return f"Dynamic execution failed: {e}"
    else:
        return "Cancelled"


#################################################################################
#--------------------------------------Finish------------------------------------
#################################################################################



# --------------- Rule-based fallback (offline when Ollama is down) ---------------
def rule_based_intent(text: str) -> str:
    t = text.lower().strip()
    if not t or len(t) < 2:
        return "do nothing"

    # Greetings
    if "hello" in t or t == "hi" or t.startswith("hi ") or t == "hey" or t.startswith("hey ") or "greetings" in t:
        return "greet"

    # Appreciation
    if "thank you" in t or t == "thanks" or "appreciate" in t or "amazing" in t or "good job" in t or "great work" in t or "awesome" in t or "nice" in t:
        return "appreciate"

    # Files and Folders (Must be before apps so 'file' doesn't trigger 'open files')
    t_clean = re.sub(r"[^\w\s]", "", t) # remove punctuation
    if t_clean.startswith("create file "):
        filename = t_clean.replace("create file ", "", 1).strip()
        if filename:
            return f"create file {filename}"
    if t_clean.startswith("delete file "):
        filename = t_clean.replace("delete file ", "", 1).strip()
        if filename:
            return f"delete file {filename}"
    if t_clean.startswith("create folder ") or t_clean.startswith("make folder "):
        foldername = t_clean.replace("create folder ", "", 1).replace("make folder ", "", 1).strip()
        if foldername:
            return f"create folder {foldername}"
    if t_clean.startswith("delete folder ") or t_clean.startswith("remove folder "):
        foldername = t_clean.replace("delete folder ", "", 1).replace("remove folder ", "", 1).strip()
        if foldername:
            return f"delete folder {foldername}"

    # Apps
    if re.search(r"\b(open\s+)?notepad\b", t):
        return "open notepad"
    if re.search(r"\b(open\s+)?chrome\b", t):
        return "open chrome"
    if re.search(r"\b(open\s+)?edge\b", t):
        return "open edge"
    if re.search(r"\b(open\s+)?(files?|explorer|file\s+explorer)\b", t):
        return "open files"
    if re.search(r"\b(open\s+)?calculator\b", t):
        return "open calculator"
    if re.search(r"\b(open\s+)?task\s+manager\b", t):
        return "open task manager"
    if re.search(r"\b(open\s+)?settings\b", t):
        return "open settings"
    if re.search(r"\b(open\s+)?(cmd|command\s+prompt)\b", t):
        return "open cmd"
    if re.search(r"\b(open\s+)?powershell\b", t):
        return "open powershell"
    if re.search(r"\b(open\s+)?paint\b", t):
        return "open paint"
    if re.search(r"\b(open\s+)?sticky\s+notes\b", t):
        return "open sticky notes"
    if re.search(r"\b(open\s+)?desktop\b", t):
        return "open desktop"
    if re.search(r"\b(open\s+)?documents\b", t):
        return "open documents"
    if re.search(r"\b(open\s+)?downloads\b", t):
        return "open downloads"
    if (
        re.search(r"\bopen\s+chatgpt\b", t)
        or re.search(r"\bopen\s+chat\s+gpt\b", t)
        or re.search(r"\bopen\s+chat\s*gpt\b", t)
    ):
        return "open chatgpt"
    m_app = re.search(r"\bopen\s+app\s+(.+)$", t.strip())
    if m_app:
        app_name = m_app.group(1).strip()[:200]
        if app_name:
            return f"open app {app_name}"
    
    # Catch generic "open X"
    if t.startswith("open ") and len(t.split()) <= 4:
        app_name = t[5:].strip().replace("the ", "")
        known = ["notepad", "chrome", "edge", "files", "calculator", "settings", "cmd", "powershell", "paint", "desktop", "documents", "downloads", "chatgpt"]
        if app_name and app_name not in known and "url" not in app_name:
            return f"open app {app_name}"
    if re.search(r"\bopen\s+teams\b", t):
        return "open app teams"
    if re.search(r"\bopen\s+outlook\b", t):
        return "open app outlook"

    # Browser
    if ("google" in t or "chrome" in t) and ("search" in t or "find" in t):
        q = re.sub(r"^(.*?)(search|find)\s+(for\s+)?", "", t, flags=re.I)
        q = re.sub(r"\s+(on|in)\s+(google|chrome).*$", "", q, flags=re.I).strip()
        if q:
            return f"google search {q}"
    if "youtube" in t and ("search" in t or "play" in t or "find" in t or "dhundo" in t):
        q = re.sub(r"^(.*?)(search|play|find|dhundo)\s+(for\s+)?", "", t, flags=re.I)
        q = re.sub(r"\s+(on|in|pe)\s+youtube.*$", "", q, flags=re.I).strip()
        q = re.sub(r"^youtube\s*pe\s*", "", q, flags=re.I).strip()
        if q:
            return f"youtube search {q}"
        return "youtube search " + t.replace("youtube", "").replace("search", "").replace("play", "").replace("dhundo", "").replace("pe", "").strip() or "music"
    # Handle "youtube pe <query>" even when user does not say "search/play"
    m_yt = re.search(r"\byoutube\s*pe\s+(.+)$", t, flags=re.I)
    if m_yt:
        q = m_yt.group(1).strip()
        if q:
            return f"youtube search {q}"
        
    # WhatsApp
    m_wa = re.search(r"whatsapp\s+(.+?)\s+ko\s+message\s+bhejo\s+(.+)$", t)
    if m_wa:
        return f"whatsapp message {m_wa.group(1).strip()} | {m_wa.group(2).strip()}"
    if "open url" in t or "open website" in t or "go to" in t:
        url = t.replace("open url", "").replace("open website", "").replace("go to", "").strip()
        if url and len(url) > 3:
            if not url.startswith("http"):
                url = "https://" + url
            return f"open url {url}"

    # Mouse
    if re.search(r"\b(scroll\s+)?down\b", t) and "scroll" in t or "scroll down" in t:
        return "scroll down"
    if "scroll up" in t:
        return "scroll up"
    if "scroll left" in t:
        return "scroll left"
    if "scroll right" in t:
        return "scroll right"
    if "move mouse up" in t or "mouse up" in t:
        return "move mouse up"
    if "move mouse down" in t or "mouse down" in t:
        return "move mouse down"
    if "click center" in t or "click middle" in t or "center click" in t:
        return "click center"
    if "move left" in t or "mouse left" in t:
        return "move mouse left"
    if "move right" in t or "mouse right" in t:
        return "move mouse right"
    if "double click" in t:
        return "double click"
    if "right click" in t:
        return "right click"

    # Keyboard / typing
    if "type " in t and len(t) > 6:
        rest = t.split("type", 1)[1].strip()
        if rest and not rest.startswith("text"):
            return f"type text {rest}"
        return f"type text {rest.replace('text', '').strip()}" if rest else "do nothing"
    if re.search(r"\bpress\s+(key\s+)?(enter|tab|escape|space|backspace|delete)\b", t):
        key = re.search(r"(enter|tab|escape|space|backspace|delete)", t)
        if key:
            return f"press key {key.group(1)}"
    if "alt f4" in t or "close window" in t or "close this" in t:
        return "close window"
    if "minimize" in t:
        return "minimize window"
    if "maximize" in t:
        return "maximize window"
    if t.startswith("run command "):
        return f"run command {t.replace('run command ', '', 1).strip()}"
    if "snap left" in t or "snap window left" in t:
        return "snap window left"
    if "snap right" in t or "snap window right" in t:
        return "snap window right"
    if "show desktop" in t or "desktop" in t and "open" not in t:
        return "show desktop"
    if "task view" in t:
        return "task view"
    if "next window" in t or "switch window" in t:
        return "next window"
    if re.search(r"\bcopy\b", t) and "paste" not in t:
        m = re.search(r"\bcopy\s+(?:the\s+)?(?:text\s+)?(.+)$", t.strip())
        if m:
            rest = m.group(1).strip()
            rest = re.sub(r"\s+(from|on)\s+(the\s+)?screen\s*$", "", rest, flags=re.I).strip()
            if re.match(r"^(from|on)\s+(the\s+)?screen\s*$", rest, flags=re.I):
                return "copy"
            rest = re.sub(r"^(the\s+word\s+|the\s+words?\s+)", "", rest, flags=re.I).strip()
            if rest.lower() in ("text", "the", "the text", "the word", "words", "word"):
                return "copy"
            if rest and len(rest) <= 500:
                return f"copy text {rest}"
        return "copy"
    if "paste" in t:
        return "paste"
    if "cut" in t:
        return "cut"
    if "select all" in t:
        return "select all"
    if "undo" in t:
        return "undo"
    if "redo" in t:
        return "redo"
    if "read clipboard" in t or "clipboard" in t:
        return "read clipboard"
    if "what time" in t or "what's the time" in t or "current time" in t:
        return "what time"
    if "what date" in t or "what's the date" in t or "today's date" in t:
        return "what date"
    if "calibrate mic" in t or "microphone calibration" in t or "calibrate microphone" in t:
        return "calibrate mic"
    if "calibration status" in t or "mic status" in t:
        return "calibration status"
    if "reset calibration" in t or "clear calibration" in t:
        return "reset calibration"
    if "refresh" in t or "reload" in t:
        return "refresh"
    if "go back" in t or "back" in t and "go" in t:
        return "go back"
    if "go forward" in t or "forward" in t:
        return "go forward"
    if "new tab" in t:
        return "new tab"
    if "close tab" in t:
        return "close tab"
    if "play" in t and "pause" not in t or "play pause" in t:
        return "play pause"
    if "pause" in t and "play" not in t:
        return "play pause"
    if "next track" in t or "next song" in t:
        return "next track"
    if "previous track" in t or "previous song" in t or "last track" in t:
        return "previous track"
    if "lock computer" in t or "lock pc" in t or "lock screen" in t:
        return "lock computer"
    if "sleep" in t and "computer" in t or t.strip() == "sleep":
        return "sleep"
    if "shutdown" in t or "shut down" in t:
        return "shutdown"
    if "restart" in t or "reboot" in t:
        return "restart"

    # Screen
    if "read screen" in t or "read the screen" in t or "what's on screen" in t:
        return "read screen"
    if "screenshot" in t or "take screenshot" in t or "capture screen" in t:
        return "take screenshot"

    # Volume
    if re.search(r"\bvolume\s+up\b", t) or "turn up volume" in t:
        return "volume up"
    if re.search(r"\bvolume\s+down\b", t) or "turn down volume" in t:
        return "volume down"
    if "mute" in t and "unmute" not in t:
        return "mute volume"
    if "unmute" in t:
        return "unmute volume"

    # Repeat
    if "repeat" in t and ("last" in t or "again" in t or "that" in t):
        return "repeat last action"

    return "do nothing"


def _normalize_for_keywords(text: str) -> str:
    """Normalize transcript for keyword matching: lower, single spaces, no punctuation."""
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def keyword_catch(text: str) -> str:
    """
    Trigger actions by spotting keywords even when the full sentence is unclear.
    If any configured keyword (or all keywords in a phrase) appear in the transcript, return that action.
    """
    if not USE_KEYWORD_CATCH or not text or len(text.strip()) < KEYWORD_MIN_LEN:
        return "do nothing"
    norm = _normalize_for_keywords(text)
    if not norm:
        return "do nothing"
    for keywords, action in KEYWORD_ACTIONS:
        if all(kw in norm for kw in keywords):
            # For "youtube search" from keyword catch, try to get query from text
            if action == "youtube search":
                rest = re.sub(r"youtube|search|play|find", "", norm, flags=re.I).strip()
                rest = re.sub(r"\s+", " ", rest).strip()
                if rest and len(rest) > 1:
                    return f"youtube search {rest}"
                return "youtube search"
            return action
    return "do nothing"


def normalize_decision_action(decision: str, user_text: str = "") -> str:
    """
    Normalize imperfect LLM/rule outputs into supported canonical actions.
    Helps route near-miss YouTube intents (e.g. "open youtube and search...").
    """
    d = (decision or "").strip().lower()
    if not d:
        return "do nothing"

    if "youtube" in d:
        if d.startswith("youtube search "):
            return d

        m = re.search(r"\b(search|find|play)\s+(.+?)\s+(?:on|in|pe)\s+youtube\b", d)
        if m:
            q = m.group(2).strip(" .,!?:;")
            if q:
                return f"youtube search {q}"

        m = re.search(r"\byoutube\b.*?\b(search|find|play)\s+(?:for\s+)?(.+)$", d)
        if m:
            q = m.group(2).strip(" .,!?:;")
            q = re.sub(r"\b(on|in|pe)\s+youtube\b", "", q).strip()
            if q:
                return f"youtube search {q}"

        m = re.search(r"\byoutube(?:\s+pe)?\s+(.+)$", d)
        if m:
            q = m.group(1).strip(" .,!?:;")
            q = re.sub(r"\b(search|find|play)\b", "", q).strip()
            if q:
                return f"youtube search {q}"

        return "youtube search"

    if d == "open0 calculator":
        return "open calculator"

    return d


def extract_youtube_query(text: str) -> str:
    """Extract a likely YouTube query from raw transcript text."""
    t = (text or "").strip().lower()
    if not t:
        return ""

    # remove wake word if present
    if WAKE_WORD and WAKE_WORD in t:
        t = t.replace(WAKE_WORD, " ").strip()

    # Common forms:
    # "search lofi on youtube", "find xyz on youtube", "play xyz on youtube"
    m = re.search(r"\b(?:search|find|play)\s+(.+?)\s+(?:on|in|pe)\s+youtube\b", t)
    if m:
        return m.group(1).strip(" .,!?:;")

    # "youtube pe xyz dhundo", "youtube pe xyz"
    m = re.search(r"\byoutube\s*pe\s+(.+)$", t)
    if m:
        q = re.sub(r"\b(?:dhundo|search|find|play)\b", "", m.group(1), flags=re.I).strip()
        return q.strip(" .,!?:;")

    # "youtube search xyz" / "search youtube xyz"
    m = re.search(r"\byoutube\s+(?:search|find|play)\s+(.+)$", t)
    if m:
        return m.group(1).strip(" .,!?:;")
    m = re.search(r"\b(?:search|find|play)\s+youtube\s+(.+)$", t)
    if m:
        return m.group(1).strip(" .,!?:;")

    # Generic fallback: if youtube exists, strip obvious control words
    if "youtube" in t:
        q = re.sub(r"\byoutube\b", " ", t)
        q = re.sub(r"\b(?:search|find|play|on|in|pe|for|please|open)\b", " ", q)
        q = re.sub(r"\s+", " ", q).strip(" .,!?:;")
        return q

    return ""


def perform_youtube_search_input(query: str) -> None:
    """
    Reliable YouTube in-page search:
    - Try to focus browser window
    - Use '/' shortcut to focus search box
    - Paste query (fallback to typing), then Enter
    """
    q = (query or "").strip()
    if not q:
        return

    # Give Chrome a moment to come to foreground naturally after launch.
    time.sleep(1.2)

    # Single submit; do not repeat typing after first Enter.
    for _ in range(1):
        pyautogui.press("esc")
        time.sleep(0.15)
        pyautogui.press("/")
        time.sleep(0.35)
        # Do not use Ctrl+A here; if focus is wrong it selects all page content.
        if _PYPERCLIP_AVAILABLE:
            try:
                pyperclip.copy(q)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pyautogui.typewrite(q, interval=0.04)
        else:
            pyautogui.typewrite(q, interval=0.04)
        time.sleep(0.15)
        pyautogui.press("enter")
        break


def decide_action(user_text: str) -> str:
    """Decide action: Gemini first, then Ollama, then rules, then keyword catch."""
    decision = ""
    if USE_GEMINI_LLM:
        decision = ask_gemini_llm(user_text)
    if not decision or decision.strip() == "" or "do nothing" in decision:
        if USE_OLLAMA:
            decision = ask_ollama(user_text)
    if not decision or decision.strip() == "" or "do nothing" in decision:
        decision = rule_based_intent(user_text)
    if (not decision or decision.strip() == "" or decision == "do nothing") and USE_KEYWORD_CATCH:
        decision = keyword_catch(user_text)
    return normalize_decision_action(decision, user_text)


# --------------- Screen OCR (Tesseract) ---------------
# OEM 3 = LSTM; PSM 6 = single uniform text block (good for focused UI); PSM 3 = full page auto
_TESS_CONFIG_BLOCK = "--oem 3 --psm 6"
_TESS_CONFIG_PAGE = "--oem 3 --psm 3"


def _ensure_tesseract_cmd() -> None:
    if PATH_TESSERACT and os.path.isfile(PATH_TESSERACT):
        pytesseract.pytesseract.tesseract_cmd = PATH_TESSERACT


def preprocess_image_for_ocr(img: "Image.Image") -> "Image.Image":
    """Grayscale, contrast, mild sharpen, 2× upscale — improves UI text OCR."""
    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    gray = img.convert("L")
    gray = ImageOps.autocontrast(gray, cutoff=1)
    gray = ImageEnhance.Sharpness(gray).enhance(1.25)
    w, h = gray.size
    max_side = 8000
    gray = gray.resize(
        (min(w * 2, max_side), min(h * 2, max_side)),
        Image.LANCZOS,
    )
    return gray


def _ocr_word_entries(img: "Image.Image", config: str) -> list[dict]:
    """Parse image_to_data into word entries with line/block for phrase matching."""
    d = pytesseract.image_to_data(img, config=config, output_type=pytesseract.Output.DICT)
    n = len(d.get("text", []))
    words: list[dict] = []
    for i in range(n):
        txt = (d["text"][i] or "").strip()
        try:
            conf = int(d["conf"][i])
        except (ValueError, TypeError, KeyError):
            conf = -1
        if conf < 0 or not txt:
            continue
        words.append(
            {
                "text": txt,
                "line": d["line_num"][i],
                "block": d["block_num"][i],
                "par": d["par_num"][i],
            }
        )
    return words


def _norm_ocr_token(s: str) -> str:
    return re.sub(r"[^\w]", "", (s or "").lower())


def _find_phrase_in_word_sequence(words: list[dict], phrase: str) -> str | None:
    """Match consecutive OCR words to the user phrase (punctuation-tolerant)."""
    tokens = [_norm_ocr_token(t) for t in phrase.split() if _norm_ocr_token(t)]
    if not tokens:
        return None
    ocr_tokens = [_norm_ocr_token(w["text"]) for w in words]
    m = len(tokens)
    for i in range(len(words) - m + 1):
        if ocr_tokens[i : i + m] == tokens:
            return " ".join(words[j]["text"] for j in range(i, i + m))
    return None


def _extract_phrase_from_flat_ocr(ocr_text: str, phrase: str) -> str | None:
    """Find phrase in full OCR string (case/spacing tolerant)."""
    if not phrase.strip():
        return None
    ocr = ocr_text or ""
    flat = re.sub(r"\s+", " ", ocr.strip())
    pl = re.sub(r"\s+", " ", phrase.strip())
    tl = flat.lower()
    idx = tl.find(pl.lower())
    if idx >= 0:
        return flat[idx : idx + len(pl)]
    return None


def find_on_screen_text_to_copy(phrase: str) -> tuple[str | None, str]:
    """
    Locate user phrase on screen via OCR; return (exact substring to put on clipboard, error detail).
    """
    if not _OCR_AVAILABLE:
        return None, "OCR not available"
    if not phrase.strip():
        return None, "empty phrase"
    phrase = phrase.strip()[:500]
    raw = pyautogui.screenshot()
    img = preprocess_image_for_ocr(raw)
    _ensure_tesseract_cmd()

    flats: list[str] = []
    for cfg in (_TESS_CONFIG_BLOCK, _TESS_CONFIG_PAGE):
        try:
            words = _ocr_word_entries(img, cfg)
            hit = _find_phrase_in_word_sequence(words, phrase)
            if hit:
                return hit, ""
        except Exception:
            pass
        try:
            flat = (pytesseract.image_to_string(img, config=cfg) or "").strip()
            flats.append(flat)
            hit = _extract_phrase_from_flat_ocr(flat, phrase)
            if hit:
                return hit, ""
        except Exception:
            pass

    merged = "\n".join(flats)
    hit = _extract_phrase_from_flat_ocr(merged, phrase)
    if hit:
        return hit, ""
    return None, "not found"


def copy_phrase_to_clipboard(phrase: str) -> str:
    """OCR screen, copy only the matched phrase to the clipboard (pyperclip)."""
    if not _PYPERCLIP_AVAILABLE:
        return "Clipboard not available"
    found, err = find_on_screen_text_to_copy(phrase)
    if not found:
        return (
            f'Could not find "{phrase[:60]}" on screen. '
            f"{err or 'Try clearer text or zoom in.'}"
        )
    try:
        pyperclip.copy(found)
        preview = found[:80] + ("..." if len(found) > 80 else "")
        return f"Copied to clipboard: {preview}"
    except Exception as e:
        return f"Clipboard error: {e}"


def ocr_screen_for_reading(max_chars: int = 900) -> str:
    """Single capture, preprocessed OCR; pick richer result from two page-segmentation modes."""
    if not _OCR_AVAILABLE:
        return ""
    raw = pyautogui.screenshot()
    img = preprocess_image_for_ocr(raw)
    _ensure_tesseract_cmd()
    chunks: list[str] = []
    for cfg in (_TESS_CONFIG_BLOCK, _TESS_CONFIG_PAGE):
        try:
            chunks.append((pytesseract.image_to_string(img, config=cfg) or "").strip())
        except Exception:
            chunks.append("")
    text = max(chunks, key=len) if chunks else ""
    if not text.strip() and chunks:
        text = chunks[0] or ""
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text[:max_chars]


def open_url_in_browser(url: str) -> None:
    """Open a https URL in Chrome when path is set; same behavior as open url."""
    if PATH_CHROME and os.path.isfile(PATH_CHROME):
        subprocess.Popen([PATH_CHROME, url])
    else:
        subprocess.Popen(["chrome", url])


def resolve_app_shortcut(name: str) -> str | None:
    """Resolve shortcut name against config app_shortcuts (case-insensitive, spaces vs underscores)."""
    raw = (name or "").strip()
    if not raw:
        return None
    apps = config.get("app_shortcuts") or {}

    def norm_key(s: str) -> str:
        return re.sub(r"[\s_]+", "_", s.strip().lower())

    target = norm_key(raw)
    for k, v in apps.items():
        if not isinstance(v, str) or not v.strip():
            continue
        if norm_key(str(k)) == target:
            return v.strip()
    return None


def launch_shortcut_target(path_or_url: str) -> None:
    """Open URL in browser; otherwise run file / hand off to OS (Windows: startfile)."""
    p = os.path.expandvars(os.path.expanduser((path_or_url or "").strip()))
    if re.match(r"^https?://", p, re.I):
        open_url_in_browser(p)
        return
    if os.path.isfile(p):
        subprocess.Popen([p], shell=False)
        return
    if sys.platform == "win32":
        os.startfile(p)
    else:
        subprocess.Popen(["xdg-open", p])


# --------------- Execute actions ---------------
#def execute_action(action: str) -> str:
def execute_action(action: str, original_text: str = "") -> str:
    global last_action, last_query, CALIBRATED_NOISE_FLOOR, CALIBRATED_AT
    if not action or action == "do nothing":
        return "I did nothing"

    action = action.lower().strip()

    if action == "greet":
        last_action = action
        return "Hello Ateeb bhai. I am Nova, your voice agent."

    if action == "appreciate":
        last_action = action
        responses = [
            "Glad it actually made a difference — that's what matters.",
            "That means a lot — happy I could contribute.",
            "Anytime — keep it coming if you need more help.",
            "Haha, I'll take that — just doing my job well.",
            "Glad I could help out.",
            "Of course, happy to assist!"
        ]
        return random.choice(responses)

    if action.startswith("run command"):
        command = action.replace("run command", "").strip()
        last_action = action
        
        # Audio confirmation before doing something dangerous
        get_engine().say(f"Should I run the command: {command}?")
        get_engine().runAndWait()
        
        print(f"⚠️ Agent wants to run command: {command}")
        record_audio()
        confirmation = speech_to_text()
        
        if "yes" in confirmation or "confirm" in confirmation:
            try:
                subprocess.Popen(command, shell=True)
                return f"Executed command: {command}"
            except Exception as e:
                return f"Command execution failed: {e}"
        else:
            return "Command cancelled."

    # ----- Files and Folders -----
    if action.startswith("create file "):
        filename = action.replace("create file ", "").strip()
        desktop = get_desktop_path()
        filepath = os.path.join(desktop, filename)
        try:
            with open(filepath, 'w') as f:
                pass
            last_action = action
            return f"Created file {filename} on Desktop"
        except Exception as e:
            return f"Failed to create file: {e}"

    if action.startswith("delete file "):
        filename = action.replace("delete file ", "").strip()
        desktop = get_desktop_path()
        filepath = os.path.join(desktop, filename)
        if not os.path.exists(filepath):
            return f"File {filename} not found on Desktop"
        
        get_engine().say(f"Are you sure you want to delete the file {filename}?")
        get_engine().runAndWait()
        print(f"⚠️ Agent wants to delete file: {filepath}")
        record_audio()
        confirmation = speech_to_text()
        
        if "yes" in confirmation or "confirm" in confirmation:
            try:
                os.remove(filepath)
                return f"Deleted file {filename}"
            except Exception as e:
                return f"Failed to delete file: {e}"
        else:
            return "File deletion cancelled."

    if action.startswith("create folder "):
        foldername = action.replace("create folder ", "").strip()
        desktop = get_desktop_path()
        folderpath = os.path.join(desktop, foldername)
        try:
            os.makedirs(folderpath, exist_ok=True)
            last_action = action
            return f"Created folder {foldername} on Desktop"
        except Exception as e:
            return f"Failed to create folder: {e}"

    if action.startswith("delete folder "):
        foldername = action.replace("delete folder ", "").strip()
        desktop = get_desktop_path()
        folderpath = os.path.join(desktop, foldername)
        if not os.path.exists(folderpath):
            return f"Folder {foldername} not found on Desktop"
        
        get_engine().say(f"Are you sure you want to delete the folder {foldername}?")
        get_engine().runAndWait()
        print(f"⚠️ Agent wants to delete folder: {folderpath}")
        record_audio()
        confirmation = speech_to_text()
        
        if "yes" in confirmation or "confirm" in confirmation:
            try:
                shutil.rmtree(folderpath)
                return f"Deleted folder {foldername}"
            except Exception as e:
                return f"Failed to delete folder: {e}"
        else:
            return "Folder deletion cancelled."

    # ----- Apps -----
    if action == "open notepad":
        subprocess.Popen("notepad.exe")
        last_action = action
        return "Opening Notepad"

    if action == "open chrome":
        if CONFIRM_CHROME:
            get_engine().say("Should I open Chrome?")
            get_engine().runAndWait()
            record_audio()
            if "yes" not in speech_to_text():
                return "Cancelled"
        if PATH_CHROME and os.path.isfile(PATH_CHROME):
            subprocess.Popen([PATH_CHROME, "--start-maximized"])
        else:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "--start-maximized"])
        last_action = action
        return "Opening Chrome"

    if action == "open edge":
        if PATH_EDGE and os.path.isfile(PATH_EDGE):
            subprocess.Popen(PATH_EDGE)
        else:
            subprocess.Popen(["cmd", "/c", "start", "msedge"])
        last_action = action
        return "Opening Microsoft Edge"

    if "open files" in action:
        subprocess.Popen("explorer.exe")
        last_action = action
        return "Opening File Explorer"

    if "open calculator" in action:
        subprocess.Popen("calc.exe")
        last_action = action
        return "Opening Calculator"

    if "open task manager" in action:
        subprocess.Popen("taskmgr.exe")
        last_action = action
        return "Opening Task Manager"

    if "open settings" in action:
        subprocess.Popen(["cmd", "/c", "start", "ms-settings:"])
        last_action = action
        return "Opening Settings"

    if "open cmd" in action:
        subprocess.Popen("cmd.exe")
        last_action = action
        return "Opening Command Prompt"

    if "open powershell" in action:
        subprocess.Popen("powershell.exe")
        last_action = action
        return "Opening PowerShell"

    if "open paint" in action:
        subprocess.Popen("mspaint.exe")
        last_action = action
        return "Opening Paint"

    if "open sticky notes" in action:
        subprocess.Popen("start ms-stickynotes:", shell=True)
        last_action = action
        return "Opening Sticky Notes"

    if "open desktop" in action:
        subprocess.Popen(["explorer", os.path.join(os.environ.get("USERPROFILE", ""), "Desktop")])
        last_action = action
        return "Opening Desktop folder"

    if "open documents" in action:
        subprocess.Popen(["explorer", os.path.join(os.environ.get("USERPROFILE", ""), "Documents")])
        last_action = action
        return "Opening Documents folder"

    if "open downloads" in action:
        subprocess.Popen(["explorer", os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")])
        last_action = action
        return "Opening Downloads folder"

    a_norm = re.sub(r"\s+", " ", action.strip())
    if a_norm == "open chatgpt" or a_norm == "open chat gpt" or re.fullmatch(r"open\s+chat\s*gpt", action.strip()):
        url = resolve_app_shortcut("chatgpt") or "https://chatgpt.com"
        open_url_in_browser(url)
        last_action = action
        return "Opening ChatGPT"

    if action.startswith("open app "):
        name = action[len("open app ") :].strip()
        if not name:
            return "Say open app and the shortcut name, for example open app teams"
        target = resolve_app_shortcut(name)
        if not target:
            print(f"No config.json shortcut named '{name}'. Falling back to Windows Search...")
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.write(name, interval=0.05)
            time.sleep(1.0)
            pyautogui.press("enter")
            last_action = action
            return f"Opening {name} via Start Menu"
        try:
            launch_shortcut_target(target)
        except Exception as e:
            return f"Could not open shortcut: {e}"
        last_action = action
        return f"Opening {name}"

    # ----- WhatsApp -----
    if action.startswith("whatsapp message"):
        parts = action.replace("whatsapp message", "", 1).split("|")
        if len(parts) == 2:
            contact = parts[0].strip()
            message = parts[1].strip()
            
            # 1. Open WhatsApp
            target = resolve_app_shortcut("whatsapp")
            if target:
                launch_shortcut_target(target)
            else:
                pyautogui.press("win")
                time.sleep(0.5)
                pyautogui.write("whatsapp", interval=0.05)
                time.sleep(1.0)
                pyautogui.press("enter")
                
            time.sleep(4.0)
            
            # 2. Search the contact
            pyautogui.hotkey("ctrl", "f")
            time.sleep(1.0)
            pyautogui.write(contact, interval=0.05)
            time.sleep(2.5)
            
            # 3. Open the chat
            pyautogui.press("down")
            time.sleep(0.5)
            pyautogui.press("enter")
            time.sleep(1.5)
            
            # 4. Type the message
            pyautogui.write(message, interval=0.05)
            
            # 5. Ask: "Bhejun?"
            get_engine().say("Bhejun?")
            get_engine().runAndWait()
            
            print(f"⚠️ Agent wants to send WhatsApp message to {contact}.")
            record_audio()
            confirmation = speech_to_text()
            
            if any(word in confirmation for word in ["haan", "yes", "send", "bhej", "karo", "ha"]):
                pyautogui.press("enter")
                last_action = action
                return f"Sent WhatsApp message to {contact}"
            else:
                pyautogui.hotkey("ctrl", "a")
                pyautogui.press("backspace")
                return "WhatsApp message cancelled."
        else:
            return "Please specify both contact and message for WhatsApp."

    # ----- Web Search -----
    if action.startswith("youtube search"):
        query = action.replace("youtube search", "").strip()
        if not query:
            query = extract_youtube_query(original_text)
        if not query:
            query = last_query
        if not query:
            return "No search query detected"
        last_query = query
        last_action = f"youtube search {query}"
        
        # Open YouTube first, then type query in search box.
        if PATH_CHROME and os.path.isfile(PATH_CHROME):
            subprocess.Popen([PATH_CHROME, "--start-maximized", "https://www.youtube.com"])
        else:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "--start-maximized", "https://www.youtube.com"])

        # Wait for page load and then inject query into YouTube search.
        time.sleep(4.0)
        perform_youtube_search_input(query)

        return f"Searching YouTube for {query}"

    if action.startswith("google search") or action.startswith("chrome search"):
        query = action.replace("google search", "").replace("chrome search", "").strip() or last_query
        if not query:
            return "No search query detected"
        last_query = query
        last_action = f"google search {query}"
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        if PATH_CHROME and os.path.isfile(PATH_CHROME):
            subprocess.Popen([PATH_CHROME, "--start-maximized", url])
        else:
            subprocess.Popen(["cmd", "/c", "start", "chrome", "--start-maximized", url])
        return f"Searching Google for {query}"

    # ----- Open URL -----
    if action.startswith("open url "):
        url = action.replace("open url", "").strip()
        if not url.startswith("http"):
            url = "https://" + url
        open_url_in_browser(url)
        last_action = action
        return f"Opening {url}"

    # ----- Scroll -----
    if "scroll down" in action:
        pyautogui.scroll(-800)
        last_action = action
        return "Scrolling down"
    if "scroll up" in action:
        pyautogui.scroll(800)
        last_action = action
        return "Scrolling up"
    if "scroll left" in action:
        try:
            if hasattr(pyautogui, "hscroll"):
                pyautogui.hscroll(-200)
            else:
                pyautogui.hotkey("shift"); pyautogui.scroll(200)
        except Exception:
            pyautogui.hotkey("shift"); pyautogui.scroll(200)
        last_action = action
        return "Scrolling left"
    if "scroll right" in action:
        try:
            if hasattr(pyautogui, "hscroll"):
                pyautogui.hscroll(200)
            else:
                pyautogui.hotkey("shift"); pyautogui.scroll(-200)
        except Exception:
            pyautogui.hotkey("shift"); pyautogui.scroll(-200)
        last_action = action
        return "Scrolling right"

    # ----- Mouse -----
    if "click center" in action:
        w, h = pyautogui.size()
        pyautogui.click(w // 2, h // 2)
        last_action = action
        return "Clicked center"
    if "move mouse left" in action:
        pyautogui.moveRel(-200, 0, duration=0.3)
        last_action = action
        return "Moved mouse left"
    if "move mouse right" in action:
        pyautogui.moveRel(200, 0, duration=0.3)
        last_action = action
        return "Moved mouse right"
    if "double click" in action:
        pyautogui.doubleClick()
        last_action = action
        return "Double clicked"
    if "right click" in action:
        pyautogui.rightClick()
        last_action = action
        return "Right clicked"
    if "move mouse up" in action:
        pyautogui.moveRel(0, -200, duration=0.3)
        last_action = action
        return "Moved mouse up"
    if "move mouse down" in action:
        pyautogui.moveRel(0, 200, duration=0.3)
        last_action = action
        return "Moved mouse down"

    # ----- Clipboard / edit shortcuts -----
    if action.startswith("copy text "):
        phrase = action[len("copy text ") :].strip()
        if not phrase:
            return "Say what to copy, for example copy text hello world"
        msg = copy_phrase_to_clipboard(phrase)
        last_action = action
        return msg
    if action.strip() == "copy":
        pyautogui.hotkey("ctrl", "c")
        last_action = action
        return "Copy"
    if action.strip() == "paste":
        pyautogui.hotkey("ctrl", "v")
        last_action = action
        return "Paste"
    if action.strip() == "cut":
        pyautogui.hotkey("ctrl", "x")
        last_action = action
        return "Cut"
    if "select all" in action:
        pyautogui.hotkey("ctrl", "a")
        last_action = action
        return "Select all"
    if action.strip() == "undo":
        pyautogui.hotkey("ctrl", "z")
        last_action = action
        return "Undo"
    if action.strip() == "redo":
        pyautogui.hotkey("ctrl", "y")
        last_action = action
        return "Redo"

    # ----- Type text -----
    if action.startswith("type text "):
        to_type = action.replace("type text", "").strip()
        if to_type:
            if _PYPERCLIP_AVAILABLE:
                try:
                    pyperclip.copy(to_type)
                    pyautogui.hotkey("ctrl", "v")
                    last_action = action
                    return f"Typed: {to_type[:50]}{'...' if len(to_type) > 50 else ''}"
                except Exception:
                    pass
            pyautogui.typewrite(to_type, interval=0.05)
            last_action = action
            return f"Typed: {to_type[:50]}{'...' if len(to_type) > 50 else ''}"
        return "Nothing to type"

    # ----- Press key(s) -----
    if action.startswith("press key") or action.startswith("press keys"):
        key_str = action.replace("press keys", "").replace("press key", "").strip()
        parts = key_str.split()
        if parts:
            pyautogui.hotkey(*parts[:4])  # hotkey supports 1 to 4 keys gracefully
            last_action = action
            return f"Pressed {'+'.join(parts[:4])}"
        return "Specify keys"

    # ----- Window -----
    if "close window" in action:
        pyautogui.hotkey("alt", "f4")
        last_action = action
        return "Closing window"
    if "minimize window" in action:
        pyautogui.hotkey("win", "down")
        last_action = action
        return "Minimized window"
    if "maximize window" in action:
        pyautogui.hotkey("win", "up")
        last_action = action
        return "Maximized window"
    if "snap window left" in action:
        pyautogui.hotkey("win", "left")
        last_action = action
        return "Snapped window left"
    if "snap window right" in action:
        pyautogui.hotkey("win", "right")
        last_action = action
        return "Snapped window right"
    if "show desktop" in action:
        pyautogui.hotkey("win", "d")
        last_action = action
        return "Show desktop"
    if "task view" in action:
        pyautogui.hotkey("win", "tab")
        last_action = action
        return "Task view"
    if "next window" in action:
        pyautogui.hotkey("alt", "tab")
        last_action = action
        return "Next window"

    # ----- Screen -----
    if "read screen" in action:
        if not _OCR_AVAILABLE:
            return "OCR not available. Install pytesseract and Tesseract."
        try:
            text = ocr_screen_for_reading(900)
            last_action = action
            if text:
                return "Screen contains: " + text[:220].replace("\n", " ")
            return "No text found on screen"
        except Exception as e:
            return f"OCR error: {e}"

    if "take screenshot" in action:
        path = os.path.join(os.getcwd(), "screenshot.png")
        pyautogui.screenshot().save(path)
        last_action = action
        return f"Screenshot saved to {path}"

    if "read clipboard" in action:
        if _PYPERCLIP_AVAILABLE:
            try:
                content = pyperclip.paste() or ""
                content = (content[:300] + "..." if len(content) > 300 else content).strip()
                last_action = action
                if content:
                    return "Clipboard: " + content.replace("\n", " ")[:150]
                return "Clipboard is empty"
            except Exception as e:
                return f"Clipboard error: {e}"
        return "Clipboard not available"

    if "what time" in action:
        now = datetime.now()
        msg = now.strftime("%I %M %p").lstrip("0").replace(" 0", " ")
        last_action = action
        return f"The time is {msg}"

    if "what date" in action:
        now = datetime.now()
        msg = now.strftime("%A, %B %d, %Y")
        last_action = action
        return f"Today is {msg}"

    if "calibrate mic" in action:
        last_action = action
        return calibrate_microphone(seconds=2.0)

    if "calibration status" in action:
        last_action = action
        if CALIBRATED_NOISE_FLOOR is None:
            return "Mic is not calibrated yet"
        stamp = CALIBRATED_AT or "unknown time"
        return f"Calibration active. Noise floor {float(CALIBRATED_NOISE_FLOOR):.5f}, set at {stamp}"

    if "reset calibration" in action:
        CALIBRATED_NOISE_FLOOR = None
        CALIBRATED_AT = None
        config.setdefault("audio", {})
        config["audio"]["calibrated_noise_floor"] = None
        config["audio"]["calibrated_at"] = None
        save_config()
        last_action = action
        return "Calibration reset"

    if action.strip() == "refresh":
        pyautogui.press("f5")
        last_action = action
        return "Refresh"
    if "go back" in action:
        pyautogui.hotkey("alt", "left")
        last_action = action
        return "Go back"
    if "go forward" in action:
        pyautogui.hotkey("alt", "right")
        last_action = action
        return "Go forward"
    if "new tab" in action:
        pyautogui.hotkey("ctrl", "t")
        last_action = action
        return "New tab"
    if "close tab" in action:
        pyautogui.hotkey("ctrl", "w")
        last_action = action
        return "Close tab"

    if "play pause" in action:
        pyautogui.press("playpause")
        last_action = action
        return "Play pause"
    if "next track" in action:
        pyautogui.press("nexttrack")
        last_action = action
        return "Next track"
    if "previous track" in action:
        pyautogui.press("prevtrack")
        last_action = action
        return "Previous track"

    if "lock computer" in action:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                last_action = action
                return "Computer locked"
            except Exception as e:
                return f"Lock failed: {e}"
        return "Lock not supported on this platform"
    if action.strip() == "sleep":
        if sys.platform == "win32":
            try:
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                last_action = action
                return "Going to sleep"
            except Exception as e:
                return f"Sleep failed: {e}"
        return "Sleep not supported on this platform"
    if action.strip() == "shutdown":
        if sys.platform == "win32":
            try:
                subprocess.Popen(["shutdown", "/s", "/t", "0"])
                last_action = action
                return "Shutting down"
            except Exception as e:
                return f"Shutdown failed: {e}"
        return "Shutdown not supported on this platform"
    if action.strip() == "restart":
        if sys.platform == "win32":
            try:
                subprocess.Popen(["shutdown", "/r", "/t", "0"])
                last_action = action
                return "Restarting"
            except Exception as e:
                return f"Restart failed: {e}"
        return "Restart not supported on this platform"

    # ----- Volume -----
    if "volume up" in action:
        vol = get_volume_interface()
        if vol:
            try:
                vol.SetMasterVolumeLevelScalar(min(1.0, vol.GetMasterVolumeLevelScalar() + 0.1), None)
                last_action = action
                return "Volume up"
            except Exception:
                pass
        return "Volume control not available"
    if "volume down" in action:
        vol = get_volume_interface()
        if vol:
            try:
                vol.SetMasterVolumeLevelScalar(max(0.0, vol.GetMasterVolumeLevelScalar() - 0.1), None)
                last_action = action
                return "Volume down"
            except Exception:
                pass
        return "Volume control not available"
    if "mute volume" in action:
        vol = get_volume_interface()
        if vol:
            try:
                vol.SetMute(1, None)
                last_action = action
                return "Muted"
            except Exception:
                pass
        return "Volume control not available"
    if "unmute volume" in action:
        vol = get_volume_interface()
        if vol:
            try:
                vol.SetMute(0, None)
                last_action = action
                return "Unmuted"
            except Exception:
                pass
        return "Volume control not available"

    # ----- Repeat -----
    if "repeat last action" in action:
        if last_action:
            return execute_action(last_action)
        return "No previous action to repeat"

    # return "i did nothing"

    # ── Dynamic fallback ──────────────────────────────────────────
    print(f"⚡ No hardcoded action matched. Trying dynamic execution for: '{action}'")
    context = original_text if original_text else action  # ← add this
    code = ask_llm_for_dynamic_code(context)              # ← updated
    if code and code.strip() != "CANNOT_DO":
        result = execute_dynamic_code(code, context)      # ← updated
        if result and result != "Cancelled":
            last_action = action
        return result
    return "I don't know how to do that"

    #----end of dynamic fallback-------------------------------------


# --------------- Main loop ---------------
def main(event_callback=None):
    if sys.platform == "win32":
        try:
            import pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pass

    def emit(t, p):
        if event_callback:
            try:
                event_callback(t, p)
            except Exception as e:
                print("Event error:", e)

    emit('init', {'wake_word': WAKE_WORD, 'stop_phrase': STOP_WAKE_WORD})
    emit('status', 'Initializing...')
    print("🤖 Local Voice Agent (offline task automation)")
    print("   Wake word:", WAKE_WORD)
    print("   Stop phrase:", STOP_WAKE_WORD)
    print("   Speech: local Whisper")
    if USE_GEMINI_LLM:
        print("   Intent: Gemini", GEMINI_MODEL, "(cloud)")
    elif USE_OLLAMA:
        print("   Intent: Ollama (local)")
    else:
        print("   Intent: rules + keyword catch")
    if AUTO_CALIBRATE_ON_STARTUP:
        print(f"   Auto calibration: enabled ({AUTO_CALIBRATE_SECONDS:.1f}s)")
    else:
        print("   Auto calibration: disabled")
    print("   Press Ctrl+C to exit completely, or say 'exit agent'.\n")

    if AUTO_CALIBRATE_ON_STARTUP:
        msg = calibrate_microphone(seconds=max(0.5, AUTO_CALIBRATE_SECONDS))
        print("🔧", msg)
        get_engine().say(msg)
        get_engine().runAndWait()

    active_mode = False
    emit('status', 'Awaiting Wake Word')
    while True:
        if active_mode:
            record_audio("🎤 Speak now (listening for command)...")
        else:
            record_audio(f"💤 Waiting for wake word '{WAKE_WORD}'...")
        
        user_text = speech_to_text()

        # Check for stop phrases (handling exact phrase or misheard split words like 'stop. nova.')
        if STOP_WAKE_WORD in user_text or (("stop" in user_text or "exit" in user_text or "quit" in user_text or "bye" in user_text) and WAKE_WORD in user_text) or user_text in ["stop", "exit", "quit"]:
            print("🔴 Exiting agent completely.")
            get_engine().say("Goodbye")
            get_engine().runAndWait()
            sys.exit(0)

        if not active_mode:
            if WAKE_WORD not in user_text:
                print("😴 Wake word not detected. Ignoring.")
                continue
            active_mode = True
            emit('mode_switch', True)
            emit('status', 'Listening...')
            user_text = user_text.replace(WAKE_WORD, "").strip()
            print("🟢 Listening mode ON")
            get_engine().say("Listening mode on")
            get_engine().runAndWait()

            # If user only said wake word, wait for next command.
            if len(user_text) < 2:
                continue
        else:
            if "sleep agent" in user_text or "stop listening" in user_text:
                active_mode = False
                emit('mode_switch', False)
                emit('status', 'Awaiting Wake Word')
                print("🔴 Listening mode OFF")
                get_engine().say("Listening mode off")
                get_engine().runAndWait()
                continue

        emit('transcription', {"text": user_text, "active": active_mode})
        decision = decide_action(user_text)
        emit('decision', {'action': decision})
        print("🧠 Decided:", decision)

        if decision == "do nothing":
            print("🛑 No action taken")
            emit('status', 'Listening...')
            continue

        #result = execute_action(decision)
        result = execute_action(decision, original_text=user_text)
        emit('action_result', result)
        emit('status', 'Listening...')
        print("✅ Agent:", result)
        get_engine().say(result)
        get_engine().runAndWait()


if __name__ == "__main__":
    main()
