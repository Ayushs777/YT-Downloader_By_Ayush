# Smart YouTube Playlist Downloader & Manager

A modern, full-stack web application to download and manage YouTube playlists with high quality using `yt-dlp` and `FFmpeg`.

## 🚀 Features
- **Full Playlist Downloading**: Fetch all videos with their metadata.
- **Quality Selection**: Choose from Best, 1080p, 720p, or Audio Only (MP3).
- **Download Subtitles**: Option to download subtitles.
- **Real-Time Progress Tracking**: See download speed, ETA, and progress percentage.
- **History Dashboard**: Track and manage previously downloaded playlists.
- **SQLite / PostgreSQL Support**: Uses SQLite by default for easy local setup, easily swappable with PostgreSQL.

## 🛠️ Tech Stack
- **Backend**: Python, FastAPI, yt-dlp, FFmpeg, SQLAlchemy.
- **Frontend**: React.js, Vite, Tailwind CSS, Axios, Lucide React.

---

## 💻 Local Setup Instructions

### Prerequisites
1. **Python 3.9+** installed.
2. **Node.js 18+** installed.
3. **FFmpeg** installed and added to your system PATH.
   - *Windows*: Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) or install via `winget install ffmpeg`.
   - *Mac*: `brew install ffmpeg`
   - *Linux*: `sudo apt install ffmpeg`

### 1. Backend Setup

Open a terminal and navigate to the `backend` folder:
```bash
cd backend

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python app/main.py
```
The backend API will run at `http://localhost:8000`. 
*(Note: Downloads will be saved in the `backend/downloads` folder, and the DB `ytdownloader.db` will be generated in the backend directory).*

### 2. Frontend Setup

Open a new terminal and navigate to the `frontend` folder:
```bash
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```
The frontend will run at `http://localhost:5173`. Open this URL in your browser.

---

## 🚢 Deployment Guide (Without Docker)

To deploy this application to a production environment (like Ubuntu server, DigitalOcean, AWS, etc.):

### Backend Deployment
1. Set up a PostgreSQL database and create a database named `ytdownloader`.
2. Clone the repository to your server.
3. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/ytdownloader"
   export DOWNLOAD_DIR="/var/www/downloads"
   ```
4. Install requirements in a virtual environment.
5. Use `gunicorn` with `uvicorn` workers to run the app in production:
   ```bash
   pip install gunicorn
   gunicorn -k uvicorn.workers.UvicornWorker app.main:app -w 4 -b 0.0.0.0:8000
   ```
6. (Optional) Set up a systemd service to keep the backend running in the background.

### Frontend Deployment
1. Navigate to the `frontend` directory.
2. Build the project:
   ```bash
   npm run build
   ```
3. The build output will be in the `frontend/dist` directory.
4. Serve the `dist` folder using a web server like **Nginx** or **Apache**. 

#### Example Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # Serve Frontend
    location / {
        root /path/to/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API Requests to Backend
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🗂️ Project Structure
```text
backend/
├── app/
│   ├── main.py              # Application Entry Point
│   ├── database.py          # SQLAlchemy Setup
│   ├── models/              # DB Models & Pydantic Schemas
│   ├── routes/              # FastAPI Routes
│   └── services/            # yt-dlp Service & Download Logic
├── requirements.txt         # Python Dependencies

frontend/
├── src/
│   ├── components/          # React Components
│   ├── services/            # Axios API calls
│   ├── App.jsx              # Main UI
│   ├── main.jsx             # React Entry Point
│   └── index.css            # Tailwind Imports
├── package.json             # NPM Dependencies
├── tailwind.config.js       # Tailwind Setup
└── vite.config.js           # Vite config
```
