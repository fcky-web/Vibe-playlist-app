@app.route("/playlist", methods=["POST"])
def generate_playlist():
    data = request.get_json()
    vibe = data.get("vibe", "")
    print("Vibe received:", vibe)

    if not OPENAI_API_KEY:
        print("Missing OpenAI key")
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
        print("OpenAI response:", content)
        if not content:
            raise ValueError("Empty response from OpenAI")
        song_lines = content.strip().split("\n")
        songs = [line.strip("- ").strip() for line in song_lines if line.strip()]
    except Exception as e:
        print("OpenAI error:", e)
        return jsonify({"error": "OpenAI failed", "details": str(e)}), 500

    # ✅ Check Spotify credentials
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("Missing Spotify credentials")
        return jsonify({"error": "Missing Spotify credentials"}), 500

    auth_response = requests.post(
        "https://accounts.spotify.com/api/token",
        data={"grant_type": "client_credentials"},
        auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
    )

    print("Spotify auth status:", auth_response.status_code)
    if auth_response.status_code != 200:
        print("Spotify auth failed:", auth_response.text)
        return jsonify({"error": "Spotify auth failed", "details": auth_response.text}), 500

    token = auth_response.json().get("access_token")
    headers = {"Authorization": f"Bearer {token}"}

    # Search each song on Spotify
    playlist = []
    for song in songs:
        print("Searching song:", song)
        q = {"q": song, "type": "track", "limit": 1}
        r = requests.get("https://api.spotify.com/v1/search", headers=headers, params=q)
        results = r.json().get("tracks", {}).get("items", [])
        if results:
            track = results[0]
            playlist.append({
                "name": f"{track['name']} – {track['artists'][0]['name']}",
                "url": track['external_urls']['spotify']
            })

    print("Final playlist:", playlist)
    return jsonify({"playlist": playlist})
