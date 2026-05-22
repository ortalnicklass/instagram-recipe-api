
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import requests

app = Flask(__name__, static_folder="static")
CORS(app)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """אתה עוזר לחלץ מתכונים מטקסט. החזר JSON בלבד (ללא markdown, ללא backticks):
{"name":"...","description":"...","servings":"...","time":"...","ingredients":["..."],"steps":["..."],"tags":["..."],"found":true}
או אם אין מתכון: {"found":false,"reason":"..."}
תרגם הכל לעברית."""

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
            if not caption:
                return jsonify({"found": False, "error": "לא נמצא תוכן בסרטון."})

            ai_res = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1000,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": caption}]
                }
            )
            ai_data = ai_res.json()
            text = "".join(b.get("text","") for b in ai_data.get("content",[]))
            text = text.replace("```json","").replace("```","").strip()

            import json
            parsed = json.loads(text)
            parsed["thumbnail"] = thumbnail
            parsed["url"] = url
            return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e), "found": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
