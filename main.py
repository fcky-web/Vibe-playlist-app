import os
from flask import Flask, request, jsonify
import openai
import requests
from dotenv import load_dotenv

load_dotenv()

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Flask app
app = Flask(__name__, static_folder=".", static_url_path="")

@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/playlist", methods=["POST"])
def generate_playlist():
    data = request.get_json()
    vibe = data.get("vibe", "")

    if not OPENAI_API_KEY:
        return jsonify({"error": "Missing OpenAI API key"}), 500

    prompt = f"Suggest 5 songs that match this vibe: {vibe}. Just list the song name and artist."

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        gpt_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        content = gpt_response.choices[0].message.content if gpt_response.choices else ""
        if not content:
            raise ValueError("Empty response from OpenAI")
        song_lines = content.strip().split("\n")
        songs = [line.strip("- ").strip() for line in song_lines if line.strip()]
    except Exception as e:
        return jsonify({"error": "OpenAI failed", "details": str(e)}), 500

    # Spotify token
    auth_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
    )

    if auth_response.status_code != 200:
        return jsonify({"error": "Spotify auth failed", "details": auth_response.text}), 500

    token = auth_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Search Spotify
    playlist = []
    for song in songs:
        q = {"q": song, "type": "track", "limit": 1}
        r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=q)
        results = r.json().get("tracks", {}).get("items", [])
        if results:
            track = results[0]
            playlist.append({
                "name": f"{track['name']} – {track['artists'][0]['name']}",
                "url": track['external_urls']['spotify']
            })

    return jsonify({"playlist": playlist})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
