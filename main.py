
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import requests
import json
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder="static")
CORS(app)

ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
RECIPES_FILE = "recipes.json"

SYSTEM_PROMPT = """אתה עוזר לחלץ מתכונים מטקסט. החזר JSON בלבד (ללא markdown, ללא backticks):
{"name":"...","description":"...","servings":"...","time":"...","ingredients":["..."],"steps":["..."],"tags":["..."],"found":true}
או אם אין מתכון: {"found":false,"reason":"..."}
תרגם הכל לעברית."""

SOCIAL_DOMAINS = ["instagram.com", "facebook.com", "tiktok.com", "youtube.com", "youtu.be", "twitter.com", "x.com"]

def is_social(url):
    return any(d in url for d in SOCIAL_DOMAINS)

def fetch_web(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    res = requests.get(url, headers=headers, timeout=10)
    res.encoding = res.apparent_encoding
    soup = BeautifulSoup(res.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 20]
    thumbnail = ""
    og_img = soup.find("meta", property="og:image")
    if og_img:
        thumbnail = og_img.get("content", "")
    return "\n".join(lines[:200]), thumbnail

def load_recipes():
    try:
        if os.path.exists(RECIPES_FILE):
            with open(RECIPES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return []

def save_recipes(recipes):
    try:
        with open(RECIPES_FILE, "w", encoding="utf-8") as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)
    except:
        pass

@app.route("/")
def home():
    return send_from_directory("static", "index.html")

@app.route("/recipes", methods=["GET"])
def get_recipes():
    return jsonify(load_recipes())

@app.route("/recipes", methods=["POST"])
def add_recipe():
    recipe = request.json
    recipes = load_recipes()
    recipes.insert(0, recipe)
    save_recipes(recipes)
    return jsonify({"ok": True})

@app.route("/recipes/<int:recipe_id>", methods=["DELETE"])
def delete_recipe(recipe_id):
    recipes = load_recipes()
    recipes = [r for r in recipes if r.get("id") != recipe_id]
    save_recipes(recipes)
    return jsonify({"ok": True})

@app.route("/extract")
def extract():
    url = request.args.get("url", "")
    if not url:
        return jsonify({"error": "no url provided"}), 400
    try:
        caption = ""
        thumbnail = ""

        if is_social(url):
            ydl_opts = {"quiet": True, "skip_download": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                caption = info.get("description") or info.get("title") or ""
                thumbnail = info.get("thumbnail") or ""
        else:
            caption, thumbnail = fetch_web(url)

        if not caption:
            return jsonify({"found": False, "error": "לא נמצא תוכן בכתובת זו."})

        ai_res = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "system": SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": caption[:4000]}]
            }
        )
        ai_data = ai_res.json()
        text = "".join(b.get("text", "") for b in ai_data.get("content", []))
        text = text.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(text)
        parsed["thumbnail"] = thumbnail
        parsed["url"] = url
        return jsonify(parsed)

    except Exception as e:
        return jsonify({"error": str(e), "found": False}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
