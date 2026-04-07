import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const hasProcessed = useRef(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash;
    const sessionId = new URLSearchParams(hash.substring(1)).get('session_id');

    if (!sessionId) {
      navigate('/', { replace: true });
      return;
    }

    (async () => {
      try {
        const res = await fetch(`${API}/auth/session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ session_id: sessionId }),
        });

        if (!res.ok) throw new Error('Session exchange failed');

        const meRes = await fetch(`${API}/auth/me`, { credentials: 'include' });
        if (meRes.ok) {
          const userData = await meRes.json();
          login(userData);
          navigate('/app/assistant', { replace: true, state: { user: userData } });
        } else {
          navigate('/', { replace: true });
        }
      } catch (err) {
        console.error('Auth callback error:', err);
        navigate('/', { replace: true });
      }
    })();
  }, [navigate, login]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-[#1A1A2E] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-sm text-[#4A4A4A] font-medium tracking-wide">Authenticating...</p>
      </div>
    </div>
  );
}
