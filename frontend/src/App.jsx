import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Download,
  History,
  PlayCircle,
  Youtube,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Trash2,
  Folder,
  Settings,
  ShieldCheck,
  ChevronRight,
  Monitor,
  Music,
  ChevronDown,
} from 'lucide-react';
import {
  analyzePlaylist,
  startDownload,
  getProgress,
  getHistory,
  clearHistory,
} from './services/api';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
  return twMerge(clsx(inputs));
}

function App() {
  const [activeTab, setActiveTab] = useState('download');
  const [url, setUrl] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [playlistInfo, setPlaylistInfo] = useState(null);
  const [quality, setQuality] = useState('best');
  const [downloadSubtitles, setDownloadSubtitles] = useState(false);
  const [embedMetadata, setEmbedMetadata] = useState(true);
  const [saveLocation, setSaveLocation] = useState('');
  const [downloading, setDownloading] = useState(false);
  const [currentDownloadId, setCurrentDownloadId] = useState(null);
  const [progress, setProgress] = useState(null);
  const [history, setHistory] = useState([]);
  const [selectedVideos, setSelectedVideos] = useState(new Set());
  const [startFrom, setStartFrom] = useState('');
  const [showSettings, setShowSettings] = useState(false);

  // ---------- Fetch history when tab switches ----------
  useEffect(() => {
    if (activeTab === 'history') fetchHistory();
  }, [activeTab]);

  // ---------- Poll progress while downloading ----------
  useEffect(() => {
    let interval;
    if (downloading && currentDownloadId) {
      interval = setInterval(async () => {
        try {
          const data = await getProgress(currentDownloadId);
          setProgress(data);
          if (data.status === 'completed' || data.status === 'failed') {
            setDownloading(false);
            clearInterval(interval);
            fetchHistory();
          }
        } catch (err) {
          console.error('Progress poll error', err);
        }
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [downloading, currentDownloadId]);

  const fetchHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data);
    } catch (err) {
      console.error('History fetch error', err);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Clear all history?")) return;
    try {
      await clearHistory();
      fetchHistory();
    } catch (err) {
      console.error('History clear error', err);
    }
  };

  const handleAnalyze = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setAnalyzing(true);
    setPlaylistInfo(null);
    setDownloading(false);
    setProgress(null);
    try {
      const data = await analyzePlaylist(url);
      setPlaylistInfo(data);
      if (data.videos) setSelectedVideos(new Set(data.videos.map((_, i) => i)));
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
    }
    setAnalyzing(false);
  };

  const handleStartDownload = async () => {
    try {
      if (selectedVideos.size === 0 && playlistInfo?.videos) {
        alert("Select at least one video.");
        return;
      }
      setDownloading(true);
      const data = await startDownload({
        url,
        quality,
        download_subtitles: downloadSubtitles,
        playlist_items: Array.from(selectedVideos).map(i => i + 1).join(','),
        title: playlistInfo.title,
        total_videos: playlistInfo.total_videos,
        save_location: saveLocation,
        embed_metadata: embedMetadata,
      });
      setCurrentDownloadId(data.id);
    } catch (error) {
      alert(`Error: ${error.response?.data?.detail || error.message}`);
      setDownloading(false);
    }
  };

  const fmtDuration = (sec) => {
    if (!sec) return '--:--';
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div className="flex h-screen bg-[#0a0a0a] text-white">
      {/* Sidebar */}
      <aside className="w-64 bg-[#111] border-r border-white/5 flex flex-col">
        <div className="p-6 flex items-center gap-3">
          <div className="p-2 bg-red-600 rounded-lg shadow-lg">
            <Youtube className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-black tracking-tighter">STUDIO</span>
        </div>

        <nav className="flex-1 px-3 space-y-1 mt-4">
          <button
            onClick={() => setActiveTab('download')}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-bold",
              activeTab === 'download' ? "bg-red-600 text-white shadow-lg shadow-red-600/20" : "text-gray-500 hover:bg-white/5 hover:text-white"
            )}
          >
            <Download className="w-5 h-5" /> Downloader
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={cn(
              "w-full flex items-center gap-3 px-4 py-3 rounded-xl transition-all font-bold",
              activeTab === 'history' ? "bg-red-600 text-white shadow-lg shadow-red-600/20" : "text-gray-500 hover:bg-white/5 hover:text-white"
            )}
          >
            <History className="w-5 h-5" /> History
          </button>
        </nav>

        <div className="p-4 border-t border-white/5 space-y-4">
           <button 
             onClick={() => setShowSettings(!showSettings)}
             className="w-full flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-all"
           >
             <div className="flex items-center gap-2 text-xs font-bold text-gray-400">
               <Settings className="w-4 h-4" /> SETTINGS
             </div>
             <ChevronDown className={cn("w-4 h-4 transition-transform", showSettings && "rotate-180")} />
           </button>

           <div className="text-center space-y-2 pt-2 border-t border-white/5">
             <p className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Developed By Ayush</p>
             <div className="flex justify-center gap-4">
               <a href="https://www.linkedin.com/in/ayush777" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-blue-500 transition-colors" title="LinkedIn">
                 <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/></svg>
               </a>
               <a href="https://ayush-portfolio-2-0-o72l.vercel.app/" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors" title="Portfolio">
                 <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>
               </a>
             </div>
           </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-12 bg-gradient-to-br from-[#0a0a0a] to-[#111]">
        <div className="max-w-4xl mx-auto space-y-8">
          <AnimatePresence mode="wait">
            {activeTab === 'download' ? (
              <motion.div key="dl" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-6">
                <div className="space-y-1">
                  <h1 className="text-4xl font-black">Fast Downloader</h1>
                  <p className="text-gray-500 font-medium">Paste link below to start</p>
                </div>

                {/* Input area */}
                <div className="bg-[#181818] p-2 rounded-2xl border border-white/5 shadow-2xl flex gap-2">
                  <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="YouTube Playlist or Video URL"
                    className="flex-1 bg-transparent px-6 py-4 text-lg focus:outline-none placeholder:text-gray-600 font-medium"
                  />
                  <button
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="bg-red-600 hover:bg-red-700 disabled:opacity-50 px-10 rounded-xl font-black text-sm uppercase tracking-widest transition-all flex items-center gap-2 shadow-xl shadow-red-600/20"
                  >
                    {analyzing ? <RefreshCw className="w-5 h-5 animate-spin" /> : <>Analyze <ChevronRight className="w-4 h-4" /></>}
                  </button>
                </div>

                {/* Settings Panel */}
                <AnimatePresence>
                  {showSettings && (
                    <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                      <div className="bg-[#181818] border border-white/5 rounded-2xl p-6 grid grid-cols-2 gap-6">
                        <div className="space-y-3">
                          <label className="text-[10px] font-black text-gray-500 tracking-widest uppercase">Save Folder</label>
                          <input 
                            type="text" 
                            placeholder="Default: ./downloads"
                            value={saveLocation}
                            onChange={(e) => setSaveLocation(e.target.value)}
                            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-red-600 outline-none"
                          />
                        </div>
                        <div className="space-y-3">
                          <label className="text-[10px] font-black text-gray-500 tracking-widest uppercase">Processing</label>
                          <div className="flex gap-4">
                            <button 
                              onClick={() => setEmbedMetadata(!embedMetadata)}
                              className={cn("px-4 py-2 rounded-lg text-xs font-bold border transition-all", embedMetadata ? "bg-red-600/10 border-red-600 text-red-500" : "bg-white/5 border-white/10 text-gray-500")}
                            >
                              Metadata & Thumbnails
                            </button>
                            <button 
                              onClick={() => setDownloadSubtitles(!downloadSubtitles)}
                              className={cn("px-4 py-2 rounded-lg text-xs font-bold border transition-all", downloadSubtitles ? "bg-red-600/10 border-red-600 text-red-500" : "bg-white/5 border-white/10 text-gray-500")}
                            >
                              Subtitles
                            </button>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Playlist View */}
                {playlistInfo && (
                  <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="bg-[#181818] rounded-3xl border border-white/10 overflow-hidden shadow-2xl">
                    <div className="p-8 border-b border-white/5 bg-white/2 flex justify-between items-center">
                      <div className="space-y-1">
                        <h2 className="text-2xl font-bold">{playlistInfo.title}</h2>
                        <div className="flex gap-4 text-xs font-bold text-gray-500 uppercase tracking-widest">
                          <span className="flex items-center gap-1"><PlayCircle className="w-3 h-3" /> {playlistInfo.total_videos} Videos</span>
                          <span className="flex items-center gap-1"><Monitor className="w-3 h-3" /> {playlistInfo.uploader}</span>
                        </div>
                      </div>
                      <select
                        value={quality}
                        onChange={(e) => setQuality(e.target.value)}
                        className="bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-xs font-bold focus:border-red-600 outline-none"
                      >
                        <option value="best">BEST QUALITY</option>
                        <option value="1080p">1080P HD</option>
                        <option value="720p">720P HD</option>
                        <option value="audio-only">AUDIO ONLY (MP3)</option>
                      </select>
                    </div>

                    <div className="p-6 space-y-6">
                      <div className="max-h-60 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
                        {playlistInfo.videos.map((v, i) => (
                          <div 
                            key={i} 
                            onClick={() => {
                              const next = new Set(selectedVideos);
                              next.has(i) ? next.delete(i) : next.add(i);
                              setSelectedVideos(next);
                            }}
                            className={cn("flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border", selectedVideos.has(i) ? "bg-red-600/10 border-red-600/30" : "bg-white/2 border-transparent hover:bg-white/5")}
                          >
                            <div className="flex items-center gap-4">
                              <div className={cn("w-5 h-5 rounded border flex items-center justify-center transition-all", selectedVideos.has(i) ? "bg-red-600 border-red-600" : "bg-black/40 border-white/10")}>
                                {selectedVideos.has(i) && <CheckCircle className="w-3 h-3 text-white" />}
                              </div>
                              <span className="text-sm font-medium truncate max-w-md">{v.title}</span>
                            </div>
                            <span className="text-[10px] font-mono text-gray-500">{fmtDuration(v.duration)}</span>
                          </div>
                        ))}
                      </div>

                      <div className="pt-6 border-t border-white/5">
                        {downloading || progress ? (
                          <div className="bg-black/40 p-6 rounded-2xl border border-white/5 space-y-6">
                            <div className="flex justify-between items-center">
                              <h3 className="font-bold flex items-center gap-2">
                                {progress?.status === 'completed' ? <><CheckCircle className="text-green-500" /> COMPLETED</> : 
                                 progress?.status === 'failed' ? <><AlertCircle className="text-red-500" /> FAILED</> : 
                                 <><RefreshCw className="animate-spin text-red-500" /> DOWNLOADING...</>}
                              </h3>
                              <span className="text-xs font-mono text-gray-500">{progress?.downloaded_videos || 0} / {progress?.total_videos || 0} VIDEOS</span>
                            </div>

                            <div className="w-full bg-white/5 rounded-full h-2 overflow-hidden">
                              <div 
                                className={cn("h-full transition-all duration-500", progress?.status === 'completed' ? "bg-green-500" : "bg-red-600")}
                                style={{ width: `${progress?.status === 'completed' ? 100 : ((progress?.downloaded_videos || 0) / (progress?.total_videos || 1)) * 100}%` }}
                              />
                            </div>

                            {progress?.status !== 'completed' && progress?.status !== 'failed' && (
                              <div className="grid grid-cols-2 gap-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">
                                <div className="bg-black/40 p-3 rounded-lg border border-white/5 flex justify-between">
                                  <span>SPEED</span>
                                  <span className="text-red-500">{progress?.speed || '0.0 MiB/s'}</span>
                                </div>
                                <div className="bg-black/40 p-3 rounded-lg border border-white/5 flex justify-between">
                                  <span>ETA</span>
                                  <span className="text-white">{progress?.eta || '--:--'}</span>
                                </div>
                              </div>
                            )}

                            {(progress?.status === 'completed' || progress?.status === 'failed') && (
                              <button onClick={() => {setDownloading(false); setProgress(null);}} className="w-full bg-white/5 hover:bg-white/10 py-3 rounded-xl font-bold transition-all border border-white/10 text-xs">
                                DONE / DOWNLOAD ANOTHER
                              </button>
                            )}
                          </div>
                        ) : (
                          <button 
                            onClick={handleStartDownload}
                            className="w-full bg-red-600 hover:bg-red-700 py-5 rounded-2xl font-black text-lg uppercase tracking-widest transition-all shadow-2xl shadow-red-600/30 active:scale-95"
                          >
                            START DOWNLOAD
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ) : (
              /* History */
              <motion.div key="hist" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6">
                <div className="flex justify-between items-center">
                  <h1 className="text-4xl font-black">History</h1>
                  <button onClick={handleClearHistory} className="text-xs font-black text-gray-500 hover:text-red-500 transition-all flex items-center gap-2">
                    <Trash2 className="w-4 h-4" /> CLEAR ALL
                  </button>
                </div>

                <div className="grid gap-4">
                  {history.length === 0 ? <p className="text-center py-20 text-gray-600 font-bold uppercase tracking-widest">No downloads yet</p> : 
                    history.map(item => (
                      <div key={item.id} className="bg-[#181818] p-6 rounded-2xl border border-white/5 flex justify-between items-center hover:border-red-600/30 transition-all">
                        <div className="space-y-1">
                          <h3 className="font-bold text-lg">{item.title}</h3>
                          <div className="flex gap-4 text-[10px] font-black text-gray-500 uppercase tracking-widest">
                            <span>{item.total_videos} VIDEOS</span>
                            <span>{item.status}</span>
                            {item.download_path && <span className="text-gray-700 truncate max-w-xs">{item.download_path}</span>}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className={cn("text-xs font-black", item.status === 'completed' ? "text-green-500" : "text-red-500")}>{item.status.toUpperCase()}</div>
                          <div className="text-[10px] font-mono text-gray-600 mt-1">{item.downloaded_videos} / {item.total_videos}</div>
                        </div>
                      </div>
                    ))
                  }
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
