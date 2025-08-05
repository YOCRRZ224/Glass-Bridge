from flask import Flask, request, render_template_string, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import platform
import subprocess
from datetime import datetime
import threading

app = Flask(__name__)
app.secret_key = "supersecretkey"
socketio = SocketIO(app, async_mode="threading")

UPLOAD_FOLDER = os.path.abspath("uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

VALID_USERNAME = "yocrrz"
VALID_PASSWORD = "rtx4090"
SHUTDOWN_PASSWORD = "killglass"
MAX_ATTEMPTS = 3
attempts = 0

EXT_ICONS = {
    "mp3": "🎵", "ogg": "🎶", "wav": "🔊",
    "py": "🐍", "js": "🟨", "html": "🌐",
    "png": "🖼️", "jpg": "🖼️", "jpeg": "🖼️", "gif": "🖼️",
    "zip": "🗜️", "rar": "📦", "pdf": "📄",
    "txt": "📄", "exe": "💻", "apk": "📱",
}

def get_icon(filename):
    ext = filename.split(".")[-1].lower()
    return EXT_ICONS.get(ext, "📁" if os.path.isdir(os.path.join(UPLOAD_FOLDER, filename)) else "📄")

@app.route("/", methods=["GET", "POST"])
def login():
    global attempts
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing data"}), 400
        username = data.get("username")
        password = data.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session["user"] = username
            attempts = 0  # reset attempts
            return jsonify({"success": True})
        else:
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                os._exit(0)
            return jsonify({"error": f"Invalid credentials. Attempt {attempts}/{MAX_ATTEMPTS}"}), 401

    if "user" not in session:
        return render_template_string(open("index.html").read())
    return render_template_string(open("index.html").read())

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return "No file uploaded", 400
    file = request.files["file"]
    if file.filename == "":
        return "No file selected", 400
    filename = secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, filename))
    return "Uploaded", 200

@app.route("/files")
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return jsonify([
        {"name": f, "icon": get_icon(f), "is_music": f.split(".")[-1].lower() in ["mp3", "ogg", "wav"]}
        for f in files
    ])

@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

@app.route("/delete/<path:filename>", methods=["POST"])
def delete(filename):
    path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            os.rmdir(path)
        return "Deleted", 200
    except Exception as e:
        return f"Error: {e}", 400

@app.route("/system")
def system():
    try:
        result = subprocess.run(["neofetch", "--stdout"], capture_output=True, text=True)
        neofetch_output = result.stdout
    except Exception:
        neofetch_output = "NeoFetch not available"
    return jsonify({
        "host": platform.node(),
        "ip": request.remote_addr,
        "clock": datetime.now().strftime("%H:%M:%S"),
        "region": platform.system(),
        "battery": "Unknown",  # psutil removed
        "connection": "Stable",
        "neofetch": neofetch_output
    })

@app.route("/shutdown", methods=["POST"])
def shutdown():
    data = request.get_json()
    if data.get("password") == SHUTDOWN_PASSWORD:
        threading.Thread(target=lambda: os._exit(0)).start()
        return "Shutting down", 200
    return "Wrong password", 401

@socketio.on("chat")
def handle_chat(msg):
    emit("chat", msg, broadcast=True)

if __name__ == "__main__":
    threading.Thread(target=lambda: socketio.run(app, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)).start()
