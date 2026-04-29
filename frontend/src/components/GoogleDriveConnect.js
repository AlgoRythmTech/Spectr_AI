import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Check, X, Link as LinkIcon, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.NODE_ENV === 'development' ? '/api' : '/api';

// Google's official G logo as inline SVG
const GoogleLogo = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 48 48">
    <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
    <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
    <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
    <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
  </svg>
);

/**
 * Custom hook: manages Google Drive connection state + OAuth flow
 */
export function useGoogleDriveConnection() {
  const { getToken } = useAuth();
  const [status, setStatus] = useState({ connected: false, loading: true });
  const [connecting, setConnecting] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/google/status`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) { setStatus({ connected: false, loading: false }); return; }
      const data = await res.json();
      setStatus({ ...data, loading: false });
    } catch (e) {
      setStatus({ connected: false, loading: false });
    }
  }, [getToken]);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  const connect = useCallback(async () => {
    setConnecting(true);
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      const res = await fetch(`${API}/google/auth/start`, {
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error('auth/start failed');
      const { auth_url } = await res.json();
      if (!auth_url) throw new Error('no auth_url');

      // Open popup
      const popup = window.open(auth_url, 'google-oauth', 'width=550,height=700,left=' + ((window.innerWidth - 550) / 2) + ',top=' + ((window.innerHeight - 700) / 2));

      // Poll status every 1s until connected or popup closed
      const pollInterval = setInterval(async () => {
        if (popup?.closed) {
          clearInterval(pollInterval);
          setConnecting(false);
          fetchStatus();
          return;
        }
        try {
          const s = await fetch(`${API}/google/status`, {
            headers: { 'Authorization': `Bearer ${token}` },
            credentials: 'include',
          });
          if (s.ok) {
            const d = await s.json();
            if (d.connected) {
              clearInterval(pollInterval);
              try { popup?.close(); } catch {}
              setConnecting(false);
              setStatus({ ...d, loading: false });
            }
          }
        } catch {}
      }, 1000);

      // Safety timeout 5min
      setTimeout(() => { clearInterval(pollInterval); setConnecting(false); }, 300000);
    } catch (e) {
      console.error('Google connect failed', e);
      setConnecting(false);
    }
  }, [getToken, fetchStatus]);

  const disconnect = useCallback(async () => {
    try {
      let token = '';

      try { token = await getToken() || token; } catch { /**/ }
      try { token = await getToken() || token; } catch {}
      await fetch(`${API}/google/disconnect`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        credentials: 'include',
      });
      setStatus({ connected: false, loading: false });
    } catch (e) { console.error(e); }
  }, [getToken]);

  return { status, connecting, connect, disconnect, refresh: fetchStatus };
}

/**
 * Sidebar footer — shows Connect button or connected email with dropdown
 */
export function GoogleDriveStatusChip({ compact = false }) {
  const { status, connecting, connect, disconnect } = useGoogleDriveConnection();
  const [showMenu, setShowMenu] = useState(false);

  if (status.loading) {
    return (
      <div style={{ padding: '8px 10px', fontSize: 11, color: '#AAA', display: 'flex', alignItems: 'center', gap: 6 }}>
        <Loader2 style={{ width: 11, height: 11, animation: 'spin 0.8s linear infinite' }} />
        Loading…
      </div>
    );
  }

  if (!status.connected) {
    return (
      <motion.button
        whileHover={{ backgroundColor: '#F5F5F5' }}
        whileTap={{ scale: 0.98 }}
        onClick={connect}
        disabled={connecting}
        style={{
          width: '100%', padding: '9px 12px', display: 'flex', alignItems: 'center', gap: 8,
          background: '#fff', border: '1px solid #EBEBEB', borderRadius: 8,
          fontSize: 12, fontWeight: 600, color: '#444', cursor: connecting ? 'default' : 'pointer',
          fontFamily: 'inherit', transition: 'all 0.2s',
        }}>
        {connecting ? <Loader2 style={{ width: 12, height: 12, animation: 'spin 0.8s linear infinite' }} /> : <GoogleLogo size={12} />}
        {connecting ? 'Connecting…' : 'Connect Google Drive'}
      </motion.button>
    );
  }

  return (
    <div style={{ position: 'relative' }}>
      <motion.button
        whileHover={{ backgroundColor: '#F5F5F5' }}
        onClick={() => setShowMenu(!showMenu)}
        style={{
          width: '100%', padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 8,
          background: showMenu ? '#F5F5F5' : '#fff', border: '1px solid #EBEBEB', borderRadius: 8,
          cursor: 'pointer', fontFamily: 'inherit', textAlign: 'left', transition: 'all 0.2s',
        }}>
        {status.picture ? (
          <img src={status.picture} alt="" style={{ width: 20, height: 20, borderRadius: '50%', flexShrink: 0 }} />
        ) : (
          <div style={{ width: 20, height: 20, borderRadius: '50%', background: '#EBEBEB', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <GoogleLogo size={10} />
          </div>
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: '#111', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {status.name || 'Google Drive'}
          </div>
          {!compact && status.email && (
            <div style={{ fontSize: 10, color: '#888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{status.email}</div>
          )}
        </div>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
      </motion.button>

      <AnimatePresence>
        {showMenu && (
          <>
            <div style={{ position: 'fixed', inset: 0, zIndex: 50 }} onClick={() => setShowMenu(false)} />
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 4 }}
              transition={{ duration: 0.15 }}
              style={{
                position: 'absolute', bottom: '110%', left: 0, right: 0, zIndex: 51,
                background: '#fff', border: '1px solid rgba(0,0,0,0.08)', borderRadius: 10,
                boxShadow: '0 12px 40px rgba(0,0,0,0.1)', padding: 4,
                fontFamily: 'inherit',
              }}>
              <div style={{ padding: '8px 10px', fontSize: 10, color: '#AAA', textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 600 }}>
                Connected as
              </div>
              <div style={{ padding: '4px 10px 10px', fontSize: 11, color: '#555', borderBottom: '1px solid #F5F5F5', marginBottom: 4 }}>
                {status.email}
              </div>
              <button
                onClick={() => { disconnect(); setShowMenu(false); }}
                style={{
                  width: '100%', padding: '8px 10px', display: 'flex', alignItems: 'center', gap: 8,
                  background: 'none', border: 'none', borderRadius: 6, fontSize: 12, color: '#EF4444',
                  fontWeight: 600, cursor: 'pointer', textAlign: 'left', fontFamily: 'inherit',
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.06)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}>
                <LogOut style={{ width: 11, height: 11 }} />
                Disconnect Google
              </button>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
