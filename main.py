
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os

app = Flask(__name__, static_folder="static")
CORS(app)

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/extract")
def extract():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "no url provided"}), 400
    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            caption = info.get("description") or info.get("title") or ""
            thumbnail = info.get("thumbnail") or ""
            return jsonify({"caption": caption, "thumbnail": thumbnail, "title": info.get("title", ""), "found": bool(caption)})
    except Exception as e:
        return jsonify({"error": str(e), "found": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
