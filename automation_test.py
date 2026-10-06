import pyautogui
import time
import subprocess

# Open Notepad
subprocess.Popen("notepad.exe")

time.sleep(3)

# Click inside Notepad
pyautogui.click(300, 300)

time.sleep(1)

# Type text
pyautogui.typewrite("CUA Agent typing test by Ateeb bhai", interval=0.1)

print("Done")
 