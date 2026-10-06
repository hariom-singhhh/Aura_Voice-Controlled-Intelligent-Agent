import sounddevice as sd
from scipy.io.wavfile import write

fs = 44100
seconds = 5

print(sd.query_devices())

device_id = 7  # CHANGE THIS TO YOUR MIC NUMBER

print("Recording...")
audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1, device=device_id)
sd.wait()

write("test.wav", fs, audio)

print("Saved test.wav")
