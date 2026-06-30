from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.schemas import PlaylistInfo, DownloadRequest, HistoryResponse
from app.models.database import DownloadHistory
from app.services.downloader import get_playlist_info, run_download_task, download_progress

router = APIRouter()

@router.post("/analyze-playlist")
def analyze_playlist(request: DownloadRequest):
    try:
        info = get_playlist_info(request.url)
        videos = []
        entries = info.get('entries', [])
        for entry in entries:
            videos.append({
                "id": entry.get("id"),
                "title": entry.get("title", "Unknown"),
                "duration": entry.get("duration"),
                "url": entry.get("url")
            })
            
        return {
            "id": info.get("id", "Unknown"),
            "title": info.get("title", "Unknown Playlist"),
            "uploader": info.get("uploader"),
            "total_videos": len(videos),
            "videos": videos
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze playlist: {str(e)}")

@router.post("/start-download")
def start_download(request: DownloadRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        info = get_playlist_info(request.url)
        title = info.get("title", "Unknown Playlist")
        entries = info.get('entries', [])
        
        history = DownloadHistory(
            playlist_url=request.url,
            title=title,
            total_videos=len(entries),
            status="pending"
        )
        db.add(history)
        db.commit()
        db.refresh(history)
        
        background_tasks.add_task(
            run_download_task,
            history_id=history.id,
            url=request.url,
            quality=request.quality,
            download_subtitles=request.download_subtitles
        )
        
        return {"message": "Download started", "id": history.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/progress/{download_id}")
def get_progress(download_id: int):
    if download_id in download_progress:
        return download_progress[download_id]
    return {"status": "unknown", "message": "No active progress found for this ID"}

@router.get("/history", response_model=list[HistoryResponse])
def get_history(db: Session = Depends(get_db)):
    return db.query(DownloadHistory).order_by(DownloadHistory.created_at.desc()).all()
