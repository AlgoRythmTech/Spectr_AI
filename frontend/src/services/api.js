import axios from 'axios';

const API_BASE = process.env.REACT_APP_BACKEND_URL
  ? `${process.env.REACT_APP_BACKEND_URL}/api`
  : process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000/api'
    : '/api';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export default api;
