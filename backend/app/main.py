import sys
import os

# Ensure the backend/ directory is on the Python path so that
# `from app.xxx import yyy` works when running `python app/main.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

from app.database import Base, engine, SessionLocal
from app.models.database import DownloadHistory
from app.services.downloader import (
    get_playlist_info,
    run_download_task,
    download_progress,
    extract_playlist_url,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
Base.metadata.create_all(bind=engine)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173", "http://localhost", "https://yt-downloader-by-ayush.vercel.app"]}})

os.makedirs("downloads", exist_ok=True)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def read_root():
    return jsonify({"message": "Smart YouTube Playlist Downloader API is running!"})


@app.route("/api/analyze-playlist", methods=["POST"])
def analyze_playlist():
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"detail": "URL is required"}), 400

    try:
        print(f"[API] Analyzing playlist: {url}")
        info = get_playlist_info(url)  # URL cleaning happens inside
        print(f"[API] Analysis complete: {info.get('title', 'Unknown')}")
        videos = []
        entries = info.get("entries")

        if entries is None:
            # yt-dlp returned a single video (no playlist wrapper)
            videos.append({
                "id": info.get("id"),
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration"),
                "url": info.get("webpage_url") or info.get("url") or url,
            })
        else:
            for entry in entries:
                if entry:
                    videos.append({
                        "id": entry.get("id"),
                        "title": entry.get("title", "Unknown"),
                        "duration": entry.get("duration"),
                        "url": entry.get("url"),
                    })

        return jsonify({
            "id": info.get("id", "Unknown"),
            "title": info.get("title", "Unknown Playlist"),
            "uploader": info.get("uploader"),
            "total_videos": len(videos),
            "videos": videos,
        })

    except Exception as e:
        print(f"[ANALYZE ERROR] {e}")
        return jsonify({"detail": f"Failed to analyze playlist: {str(e)}"}), 400


@app.route("/api/start-download", methods=["POST"])
def start_download():
    data = request.get_json(silent=True) or {}
    raw_url = data.get("url", "").strip()
    if not raw_url:
        return jsonify({"detail": "URL is required"}), 400

    quality = data.get("quality", "best")
    download_subtitles = data.get("download_subtitles", False)
    playlist_items = data.get("playlist_items", None)
    custom_path = data.get("save_location", "").strip()
    embed_metadata = data.get("embed_metadata", True)

    # Clean the URL so download also uses the full playlist form
    url = extract_playlist_url(raw_url)

    try:
        # Optimization: If the frontend already analyzed it, use those values
        title = data.get("title")
        total = data.get("total_videos")
        
        if not title or not total:
            print(f"[API] Fetching missing metadata for download: {url}")
            info = get_playlist_info(raw_url)
            title = info.get("title", "Unknown Playlist")
            entries = info.get("entries")
            if playlist_items:
                total = len(playlist_items.split(','))
            else:
                total = len(entries) if entries else 1
        elif playlist_items:
            # If items were selected, the total is the count of selected items
            total = len(playlist_items.split(','))
        
        db = SessionLocal()
        history = DownloadHistory(
            playlist_url=url,
            title=title,
            total_videos=total,
            status="pending",
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        history_id = history.id
        db.close()

        print(f"[API] Starting download #{history_id}: {title} ({total} videos)")

        thread = threading.Thread(
            target=run_download_task,
            kwargs={
                "history_id": history_id,
                "url": url,
                "quality": quality,
                "download_subtitles": download_subtitles,
                "playlist_items": playlist_items,
                "custom_path": custom_path,
                "embed_metadata": embed_metadata,
            },
            daemon=True,
        )
        thread.start()

        return jsonify({"message": "Download started", "id": history_id})

    except Exception as e:
        print(f"[API ERROR] Start-download: {e}")
        return jsonify({"detail": str(e)}), 400


@app.route("/api/progress/<int:download_id>", methods=["GET"])
def get_progress(download_id):
    if download_id in download_progress:
        return jsonify(download_progress[download_id])
    return jsonify({
        "status": "pending",
        "progress_percent": 0,
        "speed": "waiting...",
        "eta": "--",
        "current_video": "Queued...",
        "downloaded_videos": 0,
        "total_videos": 0,
    })


@app.route("/api/history", methods=["GET"])
def get_history():
    db = SessionLocal()
    records = db.query(DownloadHistory).order_by(DownloadHistory.created_at.desc()).all()
    result = []
    for h in records:
        result.append({
            "id": h.id,
            "playlist_url": h.playlist_url,
            "title": h.title,
            "total_videos": h.total_videos,
            "downloaded_videos": h.downloaded_videos,
            "status": h.status,
            "download_path": h.download_path,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        })
    db.close()
    return jsonify(result)


@app.route("/api/history", methods=["DELETE"])
def clear_history():
    try:
        db = SessionLocal()
        db.query(DownloadHistory).delete()
        db.commit()
        db.close()
        return jsonify({"message": "History cleared successfully"})
    except Exception as e:
        return jsonify({"detail": str(e)}), 400


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("  Smart YouTube Playlist Downloader - Backend")
    print("  Server: http://localhost:8000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=8000, debug=True)
