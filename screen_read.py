import pyautogui
import pytesseract
from PIL import Image

# tell python where tesseract lives
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

img = pyautogui.screenshot()
img.save("screen.png")

text = pytesseract.image_to_string(Image.open("screen.png"))

print("SCREEN TEXT:")
print(text)
