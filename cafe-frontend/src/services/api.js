import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

// Axios instance oluştur
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auth token interceptor (sonradan ekleyeceğiz)
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// API fonksiyonları
export const apiService = {
  // Masa işlemleri
  getTables: () => api.get('/tables/'),
  getTable: (id) => api.get(`/tables/${id}/`),
  getAvailableTables: () => api.get('/tables/available/'),
  getOccupiedTables: () => api.get('/tables/occupied/'),
  
  // Seans işlemleri
  startSession: (tableId, notes = '') => 
    api.post(`/tables/${tableId}/start_session/`, { notes }),
  stopSession: (tableId) => 
    api.post(`/tables/${tableId}/stop_session/`),
  getCurrentSession: (tableId) => 
    api.get(`/tables/${tableId}/current_session/`),
  
  // Seanslar
  getSessions: () => api.get('/sessions/'),
  getActiveSessions: () => api.get('/sessions/active/'),
  getTodaySessions: () => api.get('/sessions/today/'),
  
  // PlayStation kontrolü
  getPlayStations: () => api.get('/playstation/'),
  powerOnPlayStation: (id) => api.post(`/playstation/${id}/power_on/`),
  powerOffPlayStation: (id) => api.post(`/playstation/${id}/power_off/`),
  
  // Auth işlemleri
  login: (username, password) => 
    api.post('/auth/login/', { username, password }),
  logout: () => api.post('/auth/logout/'),
};

export default api;