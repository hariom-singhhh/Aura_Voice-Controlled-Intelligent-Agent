import whisper
import pyttsx3
import sounddevice as sd
from scipy.io.wavfile import write
import pyautogui

fs = 44100
seconds = 5

engine = pyttsx3.init()
model = whisper.load_model("base")

print("Speak now...")

audio = sd.rec(int(seconds * fs), samplerate=fs, channels=1)
sd.wait()

write("mouse.wav", fs, audio)

print("Processing...")

result = model.transcribe("mouse.wav")
text = result["text"].lower().strip()

print("You said:", text)

screen_width, screen_height = pyautogui.size()

if "click center" in text:
    x = screen_width // 2
    y = screen_height // 2
    pyautogui.moveTo(x, y, duration=1)
    pyautogui.click()
    engine.say("Clicked center")

elif "move left" in text:
    pyautogui.moveRel(-200, 0, duration=1)
    engine.say("Moved left")

elif "move right" in text:
    pyautogui.moveRel(200, 0, duration=1)
    engine.say("Moved right")

elif "scroll down" in text:
    pyautogui.scroll(-3000)
    engine.say("Scrolling down")

elif "double click" in text:
    pyautogui.doubleClick()
    engine.say("Double clicked")

elif "read screen" in text:
    img = pyautogui.screenshot()
    img.save("screen.png")
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    screen_text = pytesseract.image_to_string(Image.open("screen.png"))
    print(screen_text[:300])
    engine.say("I have read the screen")


else:
    engine.say("Command not recognized")

engine.runAndWait()
