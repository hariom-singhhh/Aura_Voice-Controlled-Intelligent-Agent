import whisper
import pyttsx3
import sounddevice as sd
from scipy.io.wavfile import write
import pyautogui
import subprocess

fs = 44100
seconds = 5

engine = pyttsx3.init()
model = whisper.load_model("base")

print("Speak now...")

audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
sd.wait()

write("command.wav", fs, audio)

print("Processing...")

result = model.transcribe("command.wav")
text = result["text"].lower()

print("You said:", text)

# ===== COMMAND LOGIC =====

if "open notepad" in text:
    subprocess.Popen("notepad.exe")
    engine.say("Opening notepad")

elif "open chrome" in text:
    subprocess.Popen(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

    engine.say("Opening chrome")

elif "hello" in text:
    engine.say("Hello Ateeb bhai")

elif "open calculator" in text:
    subprocess.Popen("calc")
    engine.say("Opening calculator")

elif "close" in text:
    pyautogui.hotkey("alt", "f4")

else:
    engine.say("Sorry, I did not understand")

engine.runAndWait()
