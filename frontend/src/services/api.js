import axios from 'axios';

// Rewrite `localhost` → `127.0.0.1` to dodge the Windows+Chrome IPv6 dual-stack
// trap: Chrome tries `::1` first, uvicorn only binds IPv4, request fails with
// "Failed to fetch". This has bitten us in demos twice now.
const _rawBackend = process.env.REACT_APP_BACKEND_URL || '';
const _safeBackend = _rawBackend.replace('://localhost', '://127.0.0.1');

const API_BASE = _safeBackend
  ? `${_safeBackend}/api`
  : '/api';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export default api;
