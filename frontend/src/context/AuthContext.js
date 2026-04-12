import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // Initialize from localStorage synchronously to avoid flash
  const [user, setUser] = useState(() => {
    try {
      const saved = localStorage.getItem('dev_user');
      return saved ? JSON.parse(saved) : null;
    } catch { return null; }
  });
  const [loading, setLoading] = useState(() => !localStorage.getItem('dev_user'));
  const [firebaseUser, setFirebaseUser] = useState(null);
  const isDevSession = useRef(!!localStorage.getItem('dev_user'));

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      if (fbUser) {
        // Real Firebase user — takes priority over dev
        setFirebaseUser(fbUser);
        isDevSession.current = false;
        localStorage.removeItem('dev_user');
        try {
          const idToken = await fbUser.getIdToken();
          const res = await fetch(`${API}/auth/firebase`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${idToken}`
            },
          });
          if (res.ok) {
            const data = await res.json();
            setUser(data);
            localStorage.setItem('auth_token', idToken);
          } else {
            // Backend rejected but Firebase is valid — use Firebase info
            setUser({
              user_id: fbUser.uid,
              email: fbUser.email,
              name: fbUser.displayName || '',
              picture: fbUser.photoURL || '',
              role: 'associate'
            });
            localStorage.setItem('auth_token', idToken);
          }
        } catch (err) {
          console.error('Backend auth error:', err);
          setUser({
            user_id: fbUser.uid,
            email: fbUser.email,
            name: fbUser.displayName || '',
            picture: fbUser.photoURL || '',
            role: 'associate'
          });
          localStorage.setItem('auth_token', await fbUser.getIdToken());
        }
      } else if (!isDevSession.current) {
        // No Firebase user AND no dev session — clear everything
        setFirebaseUser(null);
        setUser(null);
        localStorage.removeItem('auth_token');
      }
      // If isDevSession.current is true, don't touch user state — dev login is active
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const loginWithGoogle = useCallback(async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      return result.user;
    } catch (error) {
      console.error('Google sign-in error:', error);
      alert('Google Auth Failed: ' + error.message + '\n\nUse the Dev Bypass button below for now.');
      throw error;
    }
  }, []);

  const devLogin = useCallback(() => {
    const mockUser = {
      user_id: "dev_partner_001",
      email: "partner@algorythm.tech",
      name: "Dev Partner",
      role: "partner",
      picture: ""
    };
    isDevSession.current = true;
    setUser(mockUser);
    setLoading(false);
    localStorage.setItem('auth_token', 'dev_mock_token_7128');
    localStorage.setItem('dev_user', JSON.stringify(mockUser));
  }, []);

  const login = (userData) => {
    setUser(userData);
  };

  const logout = useCallback(async () => {
    isDevSession.current = false;
    try {
      await signOut(auth);
    } catch (error) {
      console.error('Sign-out error:', error);
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('dev_user');
    setUser(null);
    setFirebaseUser(null);
  }, []);

  const getToken = useCallback(async () => {
    if (firebaseUser) {
      return await firebaseUser.getIdToken();
    }
    return localStorage.getItem('auth_token');
  }, [firebaseUser]);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, loginWithGoogle, devLogin, getToken }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
