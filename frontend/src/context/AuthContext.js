import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const AuthContext = createContext(null);

/**
 * Spectr auth — Google Sign-In only, no dev bypass.
 *
 * Flow:
 *   1. User clicks "Continue with Google" → Firebase popup
 *   2. On success, we exchange Firebase's ID token with our backend
 *      (`POST /api/auth/firebase`) for a session-backed user record
 *   3. The user object (with name, email, picture, user_id) becomes the
 *      source of truth for TOSAcceptanceGate's audit log
 *   4. Logging out clears Firebase + our auth_token localStorage
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [firebaseUser, setFirebaseUser] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      if (fbUser) {
        setFirebaseUser(fbUser);

        // Hydrate the user immediately from the Firebase identity so the
        // app unblocks in < 50ms. We do NOT await the backend exchange —
        // that runs in the background and merges extra fields (role) when
        // it returns. This eliminates the multi-second "Loading Spectr..."
        // pause that used to happen right after Google sign-in.
        setUser({
          user_id: fbUser.uid,
          email: fbUser.email,
          name: fbUser.displayName || '',
          picture: fbUser.photoURL || '',
          role: 'associate',
        });
        setLoading(false);

        // Backend exchange in the background — fire-and-forget
        (async () => {
          try {
            const idToken = await fbUser.getIdToken();
            localStorage.setItem('auth_token', idToken);
            const res = await fetch(`${API}/auth/firebase`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${idToken}`,
              },
            });
            if (res.ok) {
              const data = await res.json();
              // Merge in backend-only fields (role, user_id mapping) without
              // disrupting the already-hydrated identity
              setUser(prev => prev ? {
                ...prev,
                user_id: data.user_id || prev.user_id,
                role: data.role || prev.role,
              } : prev);
            }
          } catch (err) {
            console.warn('Backend auth exchange failed (non-blocking):', err?.message);
          }
        })();
      } else {
        setFirebaseUser(null);
        setUser(null);
        localStorage.removeItem('auth_token');
        setLoading(false);
      }
    });

    return () => unsubscribe();
  }, []);

  const loginWithGoogle = useCallback(async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      return result.user;
    } catch (error) {
      console.error('Google sign-in error:', error);
      // Surface a helpful message. Common causes:
      //   - auth/popup-blocked: browser popup blocker
      //   - auth/popup-closed-by-user: user dismissed the popup
      //   - auth/unauthorized-domain: Firebase console needs localhost added
      let msg = 'Google sign-in failed.';
      if (error?.code === 'auth/popup-blocked') {
        msg = 'Your browser blocked the Google sign-in popup. Please allow popups for this site and try again.';
      } else if (error?.code === 'auth/popup-closed-by-user' || error?.code === 'auth/cancelled-popup-request') {
        msg = 'Sign-in was cancelled.';
      } else if (error?.code === 'auth/unauthorized-domain') {
        msg = 'This domain isn\'t authorised for Google sign-in. Please contact support.';
      } else if (error?.message) {
        msg = error.message;
      }
      alert(msg);
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Sign-out error:', error);
    }
    localStorage.removeItem('auth_token');
    setUser(null);
    setFirebaseUser(null);
  }, []);

  const getToken = useCallback(async () => {
    if (firebaseUser) {
      return await firebaseUser.getIdToken();
    }
    return localStorage.getItem('auth_token');
  }, [firebaseUser]);

  // `login` kept for components that directly set a user (rare — mostly legacy).
  const login = (userData) => setUser(userData);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, loginWithGoogle, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
