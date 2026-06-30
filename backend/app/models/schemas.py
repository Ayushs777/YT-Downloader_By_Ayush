from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class VideoInfo(BaseModel):
    id: str
    title: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    url: str

class PlaylistInfo(BaseModel):
    id: str
    title: str
    uploader: Optional[str] = None
    videos: List[VideoInfo]
    total_videos: int

class DownloadRequest(BaseModel):
    url: str
    quality: str = "best" # best, 1080p, 720p, audio-only
    download_subtitles: bool = False

class DownloadProgress(BaseModel):
    id: int
    status: str
    progress_percent: float
    speed: str
    eta: str
    current_video: str
    downloaded_videos: int
    total_videos: int

class HistoryResponse(BaseModel):
    id: int
    playlist_url: str
    title: str
    total_videos: int
    downloaded_videos: int
    status: str
    created_at: datetime
    
    class Config:
        orm_mode = True
