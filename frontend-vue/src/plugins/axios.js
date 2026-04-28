import axios from 'axios';

const api = axios.create({
  // Aici punem adresa de baza a backend-ului tau Django
  baseURL: 'http://localhost:8000/api/',
  timeout: 5000, // daca nu rasp dupa 5 sec inchidem
  headers: {
    'Content-Type': 'application/json',
  }
});

export default api;