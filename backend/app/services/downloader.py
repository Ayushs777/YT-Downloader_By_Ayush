import yt_dlp
import os
import re
import tempfile
import urllib.parse
import traceback
import glob
import shutil
from typing import Dict, Any
from app.database import SessionLocal
from app.models.database import DownloadHistory
from datetime import datetime

DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
# Check multiple locations for cookies.txt
_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_possible_cookie_paths = [
    os.path.join(_backend_dir, "cookies.txt"),                          # backend/cookies.txt
    os.path.join(os.path.dirname(_backend_dir), "cookies.txt"),         # project_root/cookies.txt
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt"),  # app/services/cookies.txt
]
COOKIES_FILE = next((p for p in _possible_cookie_paths if os.path.exists(p)), _possible_cookie_paths[0])
CLEAN_COOKIES_FILE = os.path.join(_backend_dir, ".clean_cookies.txt")
print(f"[CONFIG] Using cookies file: {COOKIES_FILE} (exists: {os.path.exists(COOKIES_FILE)})")

# In-memory progress tracking
download_progress: Dict[int, Dict[str, Any]] = {}


def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in Windows filenames."""
    return re.sub(r'[<>:"/\\|?*]', '_', name).strip()


def extract_playlist_url(url: str) -> str:
    """
    If the URL contains a list= parameter, rewrite it to a clean playlist URL.
    """
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if 'list' in qs:
        return f"https://www.youtube.com/playlist?list={qs['list'][0]}"
    return url


def update_db_status(history_id: int, status: str, downloaded_videos: int = None):
    """Update the download history record in the database."""
    try:
        db = SessionLocal()
        history = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
        if history:
            history.status = status
            if downloaded_videos is not None:
                history.downloaded_videos = downloaded_videos
            if status in ["completed", "failed"]:
                history.completed_at = datetime.utcnow()
            db.commit()
        db.close()
    except Exception as e:
        print(f"[DB ERROR] {e}")


def set_progress(history_id: int, **kwargs):
    """Safely update download_progress dict."""
    global download_progress
    if history_id not in download_progress:
        download_progress[history_id] = {
            "status": "downloading",
            "progress_percent": 0.0,
            "speed": "Starting...",
            "eta": "calculating",
            "current_video": "Preparing...",
            "downloaded_videos": 0,
            "total_videos": 0,
        }
    download_progress[history_id].update(kwargs)


def progress_hook(d, history_id: int, total_videos: int):
    """Called by yt-dlp during download to report progress."""
    try:
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded_bytes = d.get('downloaded_bytes', 0)

            if total_bytes > 0:
                percent = round((downloaded_bytes / total_bytes) * 100, 1)
            else:
                percent_str = d.get('_percent_str', '0.0%')
                percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str).strip().rstrip('%')
                try:
                    percent = float(percent_str)
                except ValueError:
                    percent = 0.0

            speed_bytes = d.get('speed')
            if speed_bytes and speed_bytes > 0:
                speed = f"{speed_bytes / 1024 / 1024:.1f} MiB/s"
            else:
                speed = "calculating..."

            eta_seconds = d.get('eta')
            if eta_seconds is not None and eta_seconds > 0:
                mins, secs = divmod(int(eta_seconds), 60)
                eta = f"{mins:02d}:{secs:02d}"
            else:
                eta = "calculating..."

            # Format bytes
            def fmt_bytes(b):
                if not b: return "0 B"
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if b < 1024.0: return f"{b:.1f} {unit}"
                    b /= 1024.0
                return f"{b:.1f} TB"

            total_str = fmt_bytes(total_bytes)
            downloaded_str = fmt_bytes(downloaded_bytes)

            filename = os.path.basename(d.get('filename', 'unknown'))

            set_progress(
                history_id,
                status="downloading",
                progress_percent=percent,
                speed=speed,
                eta=eta,
                current_video=filename,
                total_videos=total_videos,
                downloaded_str=downloaded_str,
                total_str=total_str,
            )

        elif d['status'] == 'finished':
            current = download_progress.get(history_id, {}).get("downloaded_videos", 0) + 1
            filename = os.path.basename(d.get('filename', ''))
            set_progress(
                history_id,
                downloaded_videos=current,
                current_video=f"Finished: {filename}",
                progress_percent=0.0,
            )
            update_db_status(history_id, "downloading", current)
            print(f"[DOWNLOAD] Video {current}/{total_videos} finished: {filename}")

    except Exception as e:
        print(f"[PROGRESS HOOK ERROR] {e}")


def _sanitize_cookies():
    """
    Read the raw cookies.txt, keep only YouTube/Google cookies, and fix
    invalid include_subdomain flags that break Python's cookiejar parser.
    Uses caching to avoid re-parsing large files unless they change.
    """
    if not os.path.exists(COOKIES_FILE):
        return None

    clean_path = os.path.join(_backend_dir, ".clean_cookies.txt")
    
    # Cache Check: If clean file exists and is newer than source, use it
    if os.path.exists(clean_path):
        if os.path.getmtime(clean_path) > os.path.getmtime(COOKIES_FILE):
            return clean_path

    allowed_domains = ['.youtube.com', 'youtube.com', '.google.com', '.google.co.in', '.accounts.google.com', '.gds.google.com']
    clean_lines = ["# Netscape HTTP Cookie File", "# This is a generated file! Do not edit.", ""]

    try:
        print(f"[INFO] Sanitizing cookies file: {COOKIES_FILE}...")
        with open(COOKIES_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.rstrip('\r\n')
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) != 7:
                    continue
                domain = parts[0]
                
                # Fix: If domain starts with '.', include_subdomains (field 1) MUST be 'TRUE'
                if domain.startswith('.') and parts[1] == 'FALSE':
                    parts[1] = 'TRUE'
                
                if any(domain == d or domain.endswith(d) for d in allowed_domains):
                    clean_lines.append('\t'.join(parts))

        with open(clean_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write('\n'.join(clean_lines) + '\n')
            
        return clean_path
    except Exception as e:
        print(f"[COOKIE ERROR] {e}")
        return None

def _get_cookie_opts():
    """Return cookie options with a sanitized cookies file."""
    opts = {}
    clean_path = _sanitize_cookies()
    if clean_path:
        opts['cookiefile'] = clean_path
        print(f"[INFO] Using sanitized cookies file: {clean_path}")
    return opts


def run_download_task(
    history_id: int, 
    url: str, 
    quality: str, 
    download_subtitles: bool, 
    playlist_items: str = None,
    custom_path: str = None,
    embed_metadata: bool = True
):
    """Background task that performs the actual download via yt-dlp."""
    try:
        db = SessionLocal()
        history = db.query(DownloadHistory).filter(DownloadHistory.id == history_id).first()
        playlist_title = sanitize_filename(history.title) if history else "Unknown_Playlist"
        total_videos = history.total_videos if history else 0
        db.close()

        # Determine output directory
        if custom_path and os.path.exists(custom_path):
            base_dir = custom_path
        else:
            base_dir = DOWNLOAD_DIR
        
        output_path = os.path.join(base_dir, playlist_title)
        os.makedirs(output_path, exist_ok=True)

        # Initialize progress immediately
        set_progress(
            history_id,
            status="downloading",
            progress_percent=0.0,
            speed="Starting...",
            eta="calculating",
            current_video="Connecting to YouTube...",
            downloaded_videos=0,
            total_videos=total_videos,
        )
        update_db_status(history_id, "downloading")
        
        # Record the download path
        db = SessionLocal()
        db.query(DownloadHistory).filter(DownloadHistory.id == history_id).update({"download_path": output_path})
        db.commit()
        db.close()

        # Build yt-dlp options
        ydl_opts = {
            'outtmpl': f'{output_path}/%(title)s.%(ext)s',
            'progress_hooks': [lambda d: progress_hook(d, history_id, total_videos)],
            'noplaylist': False,
            'ignoreerrors': True,
            'retries': 10,
            'fragment_retries': 10,
            'quiet': False,
            'no_warnings': False,
            # Use Node.js as the JavaScript runtime for YouTube challenge solving
            'js_runtimes': {'node': {}},
            'writethumbnail': embed_metadata,
            'addmetadata': embed_metadata,
        }

        # Post-processors for metadata and thumbnails
        if embed_metadata:
            ydl_opts['postprocessors'] = [
                {'key': 'FFmpegMetadata', 'add_chapters': True, 'add_metadata': True},
                {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
            ]
        else:
            ydl_opts['postprocessors'] = []

        # Robust FFmpeg detection
        ffmpeg_bin = r'C:\Users\Lenovo\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin'
        if os.path.exists(os.path.join(ffmpeg_bin, "ffmpeg.exe")):
            ydl_opts['ffmpeg_location'] = ffmpeg_bin
        elif shutil.which("ffmpeg"):
            pass # Use system PATH
        else:
            # Try to find any Gyan.FFmpeg in Winget packages
            local_appdata = os.environ.get('LOCALAPPDATA', '')
            if local_appdata:
                winget_path = os.path.join(local_appdata, 'Microsoft', 'WinGet', 'Packages')
                if os.path.exists(winget_path):
                    matches = glob.glob(os.path.join(winget_path, 'Gyan.FFmpeg*', '**', 'bin'), recursive=True)
                    if matches:
                        ydl_opts['ffmpeg_location'] = matches[0]
        
        if playlist_items:
            ydl_opts['playlist_items'] = playlist_items

        # Add cookies if available
        ydl_opts.update(_get_cookie_opts())

        # Quality presets with broad fallbacks
        if quality == 'audio-only':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'].append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            })
        elif quality == '1080p':
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/bestvideo[height<=1080]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '720p':
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/bestvideo[height<=720]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        else:  # best
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'

        if download_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = ['en']

        print(f"[DOWNLOAD] Starting: {url}")
        print(f"[DOWNLOAD] Quality: {quality}, Output: {output_path}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Robust check: See how many files were actually created
        downloaded_count = download_progress.get(history_id, {}).get("downloaded_videos", 0)
        
        # Fallback: Count files in the output directory if downloaded_count is 0
        if downloaded_count == 0 and os.path.exists(output_path):
            files = [f for f in os.listdir(output_path) if f.endswith(('.mp4', '.mkv', '.webm', '.mp3', '.m4a'))]
            downloaded_count = len(files)
            print(f"[DOWNLOAD] Fallback count: {downloaded_count} files found in {output_path}")

        print(f"[DOWNLOAD] Finished. {downloaded_count}/{total_videos} videos downloaded.")

        if downloaded_count == 0 and total_videos > 0:
            raise Exception(
                "No videos were downloaded. "
                "Check your URL and network connection. "
                "If the problem persists, ensure FFmpeg is working correctly."
            )

        update_db_status(history_id, "completed", downloaded_count)
        set_progress(
            history_id,
            status="completed",
            progress_percent=100.0,
            current_video="Transmission Complete!",
            downloaded_videos=downloaded_count,
            speed="Done",
            eta="00:00",
        )

    except Exception as e:
        error_msg = str(e)
        print(f"[DOWNLOAD ERROR] {error_msg}")
        traceback.print_exc()
        update_db_status(history_id, "failed")
        set_progress(
            history_id,
            status="failed",
            current_video=f"Error: {error_msg}",
            speed="--",
            eta="--",
        )


def get_playlist_info(url: str) -> Dict[str, Any]:
    """
    Fetch playlist/video metadata without downloading.
    extract_flat=True gets the list of entries very quickly.
    """
    clean_url = extract_playlist_url(url)

    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'noplaylist': False,
        'no_warnings': True,
        'js_runtimes': {'node': {}},
    }

    # Add sanitized cookies for private/unlisted playlists
    ydl_opts.update(_get_cookie_opts())

    print(f"[YTDLP] Fetching metadata for: {clean_url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(clean_url, download=False)
        return info
