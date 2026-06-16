import axios from 'axios';

const api = axios.create({
  // Aici punem adresa de baza a backend-ului tau Django
  baseURL: '/api',
  timeout: 60000, // 60 sec — AI chat-ul poate dura mai mult
  headers: {
    'Content-Type': 'application/json',
  }
});
api.interceptors.request.use((config) => {
  // Scoatem token-ul din localStorage
  const token = localStorage.getItem('access_token');
  
  // Daca exista, il punem in header-ul cererii
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});
export default api;
