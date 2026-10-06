# Local Voice-Controlled Intelligent Agent (CUA)

Offline voice-controlled task automation for your computer using **agentic AI**. Say a wake word, then speak commands to control apps, mouse, keyboard, screen, volume, and windows—all running locally without cloud APIs.

## Features

- **Wake word**: Say **"nova"** then your command (or **"stop nova"** to interrupt).
- **Fully offline**: Speech-to-text (Whisper), optional LLM (Ollama), TTS (pyttsx3), OCR (Tesseract), and automation (pyautogui) run on your machine.
- **Robust Noise Handling**: Advanced audio preprocessing that dynamically normalizes extremely quiet microphones and accurately tracks the ambient noise floor to prevent missed commands or false triggers.
- **Fuzzy Intent Matching (Keyword Catch)**: Even if the full sentence isn't parsed perfectly or Ollama is offline, the agent will catch critical keywords to execute commands reliably.
- **System-Wide Control**: Execute arbitrary Windows terminal commands seamlessly with a built-in voice confirmation safety layer.
- **Wide task set**:
  - **Apps**: Open Notepad, Chrome, Edge, File Explorer, Calculator, Task Manager, Settings, cmd, default shortcuts (ChatGPT, Teams, Outlook), etc.
  - **Smart App Fallback**: If an app is not configured in `config.json` shortcuts (e.g. WhatsApp, VLC, Excel), it automatically searches the Windows Start Menu and launches it.
  - **Browser**: YouTube search, Google search, open any URL. Automatically launches Chrome fully maximized for the best viewing experience.
  - **Mouse**: Click center, move left/right, double click, right click, scroll up/down/left/right.
  - **Keyboard**: Type text, copy/paste/cut/undo. Robustly handles both single keys (`press key F5`) and complex hotkeys (`press keys alt tab`) without strict grammar requirements.
  - **Windows**: Close, minimize, maximize, snap left/right, virtual desktops.
  - **Screen**: Read screen (OCR), take screenshot.
  - **Volume & Media**: Volume up/down, mute/unmute, play/pause, next/previous track.
  - **System**: Lock computer, sleep, shutdown, restart, time/date checking.
  - **Terminal**: Run specific shell/powershell commands ("run command X"). Requires voice confirmation ("yes" / "confirm") before execution.
  - **Repeat**: "Repeat last action".
  - **Microphone**: "Calibrate mic" to adjust noise floor detection.

## Requirements

- **Python 3.8+**
- **Microphone** (default device used unless configured)
- **Tesseract OCR** (optional, for "read screen"): [Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
- **Ollama** (optional, for natural-language understanding): [Ollama](https://ollama.ai) with a model such as `llama3:latest`
- **Gemini API** (optional, for better understanding): set an API key to use Gemini LLM for better intent understanding

## Setup

1. **Clone or copy** this folder.

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Tesseract** (optional):  
   Install from the link above and set the path in `config.json` under `paths.tesseract` if different from the default.

5. **Install Ollama** (optional):  
   Install Ollama, run `ollama pull llama3` (or another model), and start Ollama. If Ollama is not running, the agent uses rule-based commands and keyword matching only.

6. **Configure** (optional):  
   Edit `config.json` to change wake word, audio duration, noise profile settings, paths, and custom app shortcuts.

7. **Use Gemini for better understanding** (optional):  
   Get a [Gemini API key](https://aistudio.google.com/app/apikey). In `config.json` under `api` set `gemini_api_key` to your key, then set `use_gemini_llm` to `true`.

## Usage

You can run the agent in two ways:

### 1. Web Dashboard & Widget (Recommended)
Launch the full-stack web application, which provides a cyberpunk-themed dashboard and a floating, draggable widget.
```bash
python web_app.py
```
- Open `http://127.0.0.1:5000` in your browser.
- Use the **WIDGET MODE** button to minimize the dashboard into a floating, draggable orb that stays out of your way.

### 2. Terminal Mode
Run the main agent purely in the terminal:
```bash
python voice_agent.py
```

1. Wait for **"Speak now..."**.
2. Say the wake word **"nova"** followed by your command, e.g.:
   - *"nova, open Notepad"*
   - *"nova, type text Hello world"*
   - *"nova, scroll down"*
   - *"nova, read screen"*
   - *"nova, run command ping google.com"*
   - *"nova, calibrate mic"*
   - *"stop nova"* to cancel.
3. The agent will perform the action and speak the result. Press **Ctrl+C** to exit.

## Configuration (`config.json`)

| Key | Description |
|-----|-------------|
| `wake_word` | Phrase to activate the agent (default: `"nova"`). |
| `stop_wake_word` | Phrase to stop / interrupt the agent (default: `"stop nova"`). |
| `ollama.url` / `.model` | Ollama API URL and Model name (e.g. `llama3:latest`). |
| `audio.sample_rate` | Recording sample rate (16000 recommended for Whisper). |
| `audio.preprocess_audio` | Enables noise gate and high-pass filtering (default: `true`). |
| `audio.auto_calibrate_on_startup`| Auto-calibrate mic noise floor on startup (default: `false`). |
| `use_keyword_catch` | Enable fuzzy keyword intent matching (default: `true`).|
| `app_shortcuts` | Custom voice shortcuts mapped to URLs or executable paths. |
| `paths.*` | Paths to apps like `chrome`, `edge`, and `tesseract`. |
| `whisper_model` | Whisper model: `tiny`, `base`, `small`, `medium`, `large` (default: `small`). |
| `use_ollama` | If `false`, only rule-based and keyword catch commands are used. |
| `api.gemini_api_key` | Gemini API key (Leave `null` for no cloud). |

## Offline-Only Mode

- **Without Ollama**: Set `"use_ollama": false` in `config.json`. The agent will rely on strict rules and fuzzy keyword matching for commands offline.
- **With Ollama**: Run `ollama serve` and pull a model. The agent will use the LLM to better understand intent.

## Project Structure

- **voice_agent.py** – Main loop: wake word → Audio Preprocessing → STT → intent (Gemini/Ollama/rules/keywords) → execute action → TTS.
- **config.json** – Settings, thresholds, and paths.
- **requirements.txt** – Python dependencies.

## License

Use for your minor project as needed.
