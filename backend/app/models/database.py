from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean
from app.database import Base
from datetime import datetime

class DownloadHistory(Base):
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True, index=True)
    playlist_url = Column(String, index=True)
    title = Column(String)
    total_videos = Column(Integer)
    downloaded_videos = Column(Integer, default=0)
    status = Column(String, default="pending") # pending, downloading, completed, failed
    download_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
