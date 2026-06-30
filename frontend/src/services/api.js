import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const analyzePlaylist = async (url) => {
    const response = await api.post('/analyze-playlist', { url });
    return response.data;
};

export const startDownload = async (data) => {
    const response = await api.post('/start-download', data);
    return response.data;
};

export const getProgress = async (id) => {
    const response = await api.get(`/progress/${id}`);
    return response.data;
};

export const getHistory = async () => {
    const response = await api.get('/history');
    return response.data;
};

export const clearHistory = async () => {
    const response = await api.delete('/history');
    return response.data;
};

export default api;
