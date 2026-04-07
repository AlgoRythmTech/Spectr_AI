import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { onAuthStateChanged, signInWithPopup, signOut } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';

const API = process.env.REACT_APP_BACKEND_URL ? `${process.env.REACT_APP_BACKEND_URL}/api` : '/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [firebaseUser, setFirebaseUser] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (fbUser) => {
      if (fbUser) {
        setFirebaseUser(fbUser);
        // Exchange Firebase token with our backend
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
            // Store token for subsequent API calls
            localStorage.setItem('auth_token', idToken);
          } else {
            setUser(null);
          }
        } catch (err) {
          console.error('Backend auth error:', err);
          // Still set basic user info from Firebase
          setUser({
            user_id: fbUser.uid,
            email: fbUser.email,
            name: fbUser.displayName || '',
            picture: fbUser.photoURL || '',
            role: 'associate'
          });
          localStorage.setItem('auth_token', await fbUser.getIdToken());
        }
      } else {
        setFirebaseUser(null);
        setUser(null);
        localStorage.removeItem('auth_token');
      }
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
      alert('Google Auth Failed: ' + error.message + '\n\nPlease ensure Google Auth is enabled in your Firebase Console for localhost. Use the Dev Bypass button below for now.');
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
    setUser(mockUser);
    localStorage.setItem('auth_token', 'dev_mock_token_7128');
    setLoading(false);
  }, []);

  const login = (userData) => {
    setUser(userData);
  };

  const logout = useCallback(async () => {
    try {
      await signOut(auth);
      localStorage.removeItem('auth_token');
    } catch (error) {
      console.error('Sign-out error:', error);
    }
    setUser(null);
    setFirebaseUser(null);
  }, []);

  // Helper to get current auth token for API calls
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
