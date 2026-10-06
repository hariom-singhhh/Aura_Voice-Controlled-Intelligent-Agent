import whisper
import pyttsx3
import sounddevice as sd
from scipy.io.wavfile import write

fs = 44100
seconds = 5

engine = pyttsx3.init()
model = whisper.load_model("base")

print("Speak now...")

audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
sd.wait()

write("loop.wav", fs, audio)

print("Processing...")

result = model.transcribe("loop.wav")

text = result["text"]

print("You said:", text)

engine.say(text)
engine.runAndWait()
