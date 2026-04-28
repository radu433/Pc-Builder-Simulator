import axios from 'axios';

const api = axios.create({
  // Aici punem adresa de baza a backend-ului tau Django
  baseURL: 'http://localhost:8000/api/',
  timeout: 5000, // daca nu rasp dupa 5 sec inchidem
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