# Voice Agent – Full Feature List & Permissions

This document lists **all actions** the agent can perform and the **permissions / requirements** for each.

---

## Summary

| Category        | Count | Permission note                          |
|----------------|-------|------------------------------------------|
| Apps & system  | 14    | Run as current user; no admin needed     |
| Browser        | 6     | Same as above                            |
| Mouse          | 8     | Input simulation (accessibility)         |
| Keyboard       | 12+   | Input simulation                         |
| Window         | 8     | Win key / Alt key combos                 |
| Screen         | 3     | Screenshot + OCR (Tesseract optional)    |
| Volume         | 4     | Windows audio (pycaw optional)           |
| Media          | 3     | Global media keys                        |
| System power   | 4     | Lock/sleep/shutdown/restart (user level) |
| Info           | 3     | Time, date, clipboard read               |
| Meta           | 1     | Repeat last action                       |
| Files & Folders| 4     | Desktop read/write access                |

**Overall permission:** The agent runs with **the same rights as the user** who started it. No administrator privilege is required for the listed features. For **shutdown/restart**, the user must have normal “shut down the computer” rights (default on a personal PC).

---

## 1. Apps & system (open / launch)

| # | Action              | What it does                    | Permission / requirement |
|---|---------------------|----------------------------------|---------------------------|
| 1 | Open Notepad        | Starts `notepad.exe`            | None                      |
| 2 | Open Chrome         | Starts Google Chrome            | Chrome installed; path in config if needed |
| 3 | Open Edge           | Starts Microsoft Edge           | Edge installed; path in config if needed  |
| 4 | Open File Explorer  | Opens Explorer (This PC)        | None                      |
| 5 | Open Calculator     | Starts Windows Calculator       | None                      |
| 6 | Open Task Manager   | Starts `taskmgr.exe`            | None                      |
| 7 | Open Settings       | Opens Windows Settings          | None                      |
| 8 | Open Command Prompt | Starts `cmd.exe`                | None                      |
| 9 | Open PowerShell     | Starts `powershell.exe`         | None                      |
|10 | Open Paint          | Starts `mspaint.exe`            | None                      |
|11 | Open Sticky Notes   | Starts Windows Sticky Notes     | Sticky Notes installed (Win 10/11) |
|12 | Open Desktop folder | Opens user’s Desktop in Explorer| Read access to user profile |
|13 | Open Documents      | Opens user’s Documents folder   | Read access to user profile |
|14 | Open Downloads      | Opens user’s Downloads folder   | Read access to user profile |

**Permissions:** Normal user. No admin. Needs permission to run applications and to read your user folder paths (Desktop, Documents, Downloads).

---

## 2. Browser (navigation & search)

| # | Action           | What it does                         | Permission / requirement |
|---|------------------|--------------------------------------|---------------------------|
| 1 | YouTube search   | Opens YouTube and runs search query  | Chrome/Edge; default browser behavior |
| 2 | Open URL         | Opens a given URL in browser         | Same                      |
| 3 | Refresh          | Sends F5 (refresh page)              | None                      |
| 4 | Go back          | Alt+Left (browser back)              | None                      |
| 5 | Go forward       | Alt+Right (browser forward)          | None                      |
| 6 | New tab          | Ctrl+T                               | None                      |
| 7 | Close tab        | Ctrl+W                               | None                      |

**Permissions:** None beyond input simulation. Works in whatever app has focus (usually browser).

---

## 3. Mouse

| # | Action          | What it does              | Permission / requirement |
|---|-----------------|---------------------------|---------------------------|
| 1 | Click center    | Clicks center of screen   | Input simulation          |
| 2 | Move mouse left | Moves cursor 200px left   | Input simulation          |
| 3 | Move mouse right| Moves cursor 200px right  | Input simulation          |
| 4 | Move mouse up   | Moves cursor 200px up     | Input simulation          |
| 5 | Move mouse down | Moves cursor 200px down   | Input simulation          |
| 6 | Double click    | Double‑clicks at cursor   | Input simulation          |
| 7 | Right click     | Right‑clicks at cursor    | Input simulation          |
| 8 | Scroll up       | Scrolls up                | Input simulation          |
| 9 | Scroll down     | Scrolls down              | Input simulation          |
|10 | Scroll left     | Horizontal scroll left    | Input simulation (may use Shift+wheel fallback) |
|11 | Scroll right    | Horizontal scroll right   | Same                      |

**Permissions:** Same as “ability to move mouse and click” (accessibility / input simulation). No special OS permissions.

---

## 4. Keyboard & typing

| # | Action     | What it does              | Permission / requirement |
|---|------------|---------------------------|---------------------------|
| 1 | Type text  | Types or pastes given text| Input simulation; clipboard if paste used |
| 2 | Press key  | Sends one key (e.g. Enter)| Input simulation          |
| 3 | Press keys | Sends combo (e.g. Ctrl+C) | Input simulation          |
| 4 | Copy       | Ctrl+C                    | Input simulation          |
| 5 | Paste      | Ctrl+V                    | Input simulation + clipboard |
| 6 | Cut        | Ctrl+X                    | Input simulation + clipboard |
| 7 | Select all | Ctrl+A                    | Input simulation          |
| 8 | Undo       | Ctrl+Z                    | Input simulation          |
| 9 | Redo       | Ctrl+Y                    | Input simulation          |

**Permissions:** Input simulation. Copy/Cut/Paste use system clipboard (normal user access).

---

## 5. Window management

| # | Action           | What it does           | Permission / requirement |
|---|------------------|------------------------|---------------------------|
| 1 | Close window     | Alt+F4                 | Input simulation          |
| 2 | Minimize window  | Win+Down               | Input simulation          |
| 3 | Maximize window  | Win+Up                 | Input simulation          |
| 4 | Snap window left | Win+Left               | Input simulation          |
| 5 | Snap window right| Win+Right              | Input simulation          |
| 6 | Show desktop     | Win+D                  | Input simulation          |
| 7 | Task view        | Win+Tab                | Input simulation          |
| 8 | Next window      | Alt+Tab                | Input simulation          |

**Permissions:** None beyond input simulation. Works with whatever window has focus.

---

## 6. Screen

| # | Action         | What it does                    | Permission / requirement      |
|---|----------------|----------------------------------|--------------------------------|
| 1 | Read screen    | Screenshot + OCR, speaks text   | Screenshot access; Tesseract OCR installed |
| 2 | Take screenshot| Saves screenshot to file        | Screenshot access; write to current folder |

**Permissions:**  
- **Screenshot:** Same as “can see the screen” (normal for the logged‑in user).  
- **OCR:** Tesseract must be installed and path set in config.  
- **Saving file:** Writes to the current working directory (needs write permission there).

---

## 7. Volume

| # | Action     | What it does     | Permission / requirement |
|---|------------|------------------|---------------------------|
| 1 | Volume up  | Increases volume | Windows audio API (pycaw) |
| 2 | Volume down| Decreases volume | Same                      |
| 3 | Mute       | Mutes output     | Same                      |
| 4 | Unmute     | Unmutes output   | Same                      |

**Permissions:** Uses Windows Core Audio (pycaw). Runs as current user; no admin. If pycaw is not installed, these actions report “not available”.

---

## 8. Media playback

| # | Action        | What it does      | Permission / requirement |
|---|---------------|-------------------|---------------------------|
| 1 | Play / Pause  | Media play/pause  | Global media keys         |
| 2 | Next track    | Next track        | Global media keys         |
| 3 | Previous track| Previous track    | Global media keys         |

**Permissions:** Input simulation (media keys). Works with the app that has media focus (e.g. browser, Spotify).

---

## 9. System power & lock

| # | Action        | What it does        | Permission / requirement        |
|---|---------------|---------------------|----------------------------------|
| 1 | Lock computer | Locks the session   | User right to lock workstation  |
| 2 | Sleep         | Puts PC to sleep    | User right to suspend           |
| 3 | Shutdown      | Shuts down the PC   | User right to shut down         |
| 4 | Restart       | Restarts the PC     | User right to restart           |

**Permissions:**  
- **Lock:** Normal for the logged‑in user.  
- **Sleep / Shutdown / Restart:** Standard “power user” rights. No administrator required on a typical personal PC. Group Policy can restrict these; if so, the command may fail.

---

## 10. Info (read‑only)

| # | Action        | What it does           | Permission / requirement |
|---|---------------|------------------------|---------------------------|
| 1 | What time     | Speaks current time    | None                      |
| 2 | What date     | Speaks today’s date    | None                      |
| 3 | Read clipboard| Speaks clipboard text  | Read access to clipboard  |

**Permissions:** Time/date use system clock (no special permission). Clipboard read is normal user access.

---

## 11. Meta

| # | Action             | What it does        | Permission / requirement |
|---|--------------------|---------------------|---------------------------|
| 1 | Repeat last action | Repeats last command| Same as the repeated action |

---

## 12. Files & Folders

| # | Action             | What it does        | Permission / requirement |
|---|--------------------|---------------------|---------------------------|
| 1 | Create file        | Creates an empty file on the Desktop  | Read/Write to Desktop     |
| 2 | Delete file        | Deletes a file from the Desktop       | Read/Write to Desktop     |
| 3 | Create folder      | Creates a new folder on the Desktop   | Read/Write to Desktop     |
| 4 | Delete folder      | Deletes a folder from the Desktop     | Read/Write to Desktop     |

**Permissions:** The agent dynamically resolves the true path of your Windows Desktop using the registry. It requires normal user read/write permissions to create and delete files/folders on the Desktop. Deletions are safeguarded with a mandatory voice confirmation prompt.

---

## 13. Web Interface (Dashboard & Widget)

| # | Feature            | What it does        | Permission / requirement |
|---|--------------------|---------------------|---------------------------|
| 1 | Central Dashboard  | Displays live telemetry, terminal stream, and state. | Open port 5000 (Flask)    |
| 2 | Widget Mode        | Minimizes into a floating, draggable orb. | Browser access            |
| 3 | Audio Controls     | Adjust mic sensitivity and output volume via sliders. | Browser UI                |
| 4 | Real-time Sync     | Uses SSE to instantly sync voice logic to the UI. | None                      |

**Permissions:** The web application requires access to run a local Flask server on port `5000` (or `http://127.0.0.1:5000`). It uses Server-Sent Events (SSE) to maintain a live feed of agent activity.

---

## What to allow when Windows / antivirus asks

- **Microphone:** Required for voice input.  
- **Run / execute:** The script starts other programs (Notepad, browser, etc.).  
- **Input simulation (keyboard/mouse):** Required for key presses, clicks, scroll.  
- **Screen / screenshot:** Required for “read screen” and “take screenshot”.  
- **Clipboard:** Required for paste, “type text” (paste path), and “read clipboard”.  
- **Network:** Only if you use cloud APIs (e.g. OpenAI) in config; not needed for fully offline use.

You do **not** need to run the agent “as administrator” for any of the features listed above.
