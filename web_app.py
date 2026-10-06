import json
import queue
import threading
from flask import Flask, render_template, Response, request, jsonify
import voice_agent

app = Flask(__name__)

# Thread-safe queue for SSE
event_queue = queue.Queue()

def on_agent_event(evt_type, payload):
    """Callback passed to voice_agent to receive real-time updates."""
    # Push as SSE formatted string
    data = json.dumps({"type": evt_type, "payload": payload})
    event_queue.put(f"data: {data}\n\n")

@app.route("/")
def index():
    return render_template("index.html", wake_word=voice_agent.WAKE_WORD, stop_phrase=voice_agent.STOP_WAKE_WORD)

@app.route("/events")
def events():
    def event_stream():
        while True:
            # Block until an item is available
            message = event_queue.get()
            yield message
    
    return Response(event_stream(), content_type="text/event-stream")

@app.route("/set-volume", methods=["POST"])
def set_volume():
    data = request.json
    vol_percent = float(data.get("volume", 80))
    vol_scale = vol_percent / 100.0
    
    voice_agent.TTS_VOLUME = vol_scale
    if hasattr(voice_agent, '_engine') and voice_agent._engine:
        current_mute = getattr(voice_agent, 'IS_MUTED', False)
        voice_agent._engine.setProperty('volume', 0.0 if current_mute else vol_scale)
        
    return jsonify({"status": "ok", "volume": vol_scale})

@app.route("/set-mic", methods=["POST"])
def set_mic():
    data = request.json
    sens_percent = float(data.get("sensitivity", 40))
    sens_scale = sens_percent / 100.0
    multiplier = 10.0 - (sens_scale * 9.5) 
    
    voice_agent.MIC_SENSITIVITY = sens_scale
    voice_agent.NOISE_GATE_MULTIPLIER = multiplier
    return jsonify({"status": "ok", "sensitivity": sens_scale, "multiplier": multiplier})

@app.route("/toggle-mute", methods=["POST"])
def toggle_mute():
    data = request.json
    muted = bool(data.get("muted", False))
    
    voice_agent.IS_MUTED = muted
    if hasattr(voice_agent, '_engine') and voice_agent._engine:
        vol = getattr(voice_agent, 'TTS_VOLUME', 0.8)
        voice_agent._engine.setProperty('volume', 0.0 if muted else vol)
        
    return jsonify({"status": "ok", "muted": muted})

def start_background_agent():
    print("Starting voice agent background thread...")
    # Run the voice_agent main loop, passing our callback
    agent_thread = threading.Thread(target=voice_agent.main, args=(on_agent_event,), daemon=True)
    agent_thread.start()

if __name__ == "__main__":
    start_background_agent()
    # Flask app must run on main thread (or you can use Waitress/Gunicorn, but dev server is fine for local tool)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
