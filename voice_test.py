import whisper

model = whisper.load_model("base")

print("Speak now...")

result = model.transcribe("test.wav")

print("You said:", result["text"])
