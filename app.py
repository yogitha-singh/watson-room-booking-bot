import os
import uuid
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, jsonify, request, send_from_directory
import booking
import bot
import nlu

app = Flask(__name__, static_folder="static")
booking.init()


@app.get("/")
def index():
    return send_from_directory("static", "index.html")


@app.post("/chat")
def chat():
    data = request.get_json(force=True)
    sid = data.get("session_id") or str(uuid.uuid4())
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify(error="message is required"), 400
    return jsonify(session_id=sid, reply=bot.reply(sid, msg))


@app.get("/health")
def health():
    return jsonify(status="ok", nlu="watson" if nlu._watson else "fallback")


if __name__ == "__main__":
    app.run(port=int(os.getenv("PORT", 5000)), debug=True)
