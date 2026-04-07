import { initializeApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyBCnGwmyOM4it6XPQb7nyB5yXnC_0ioCrQ",
  authDomain: "associate-research-services.firebaseapp.com",
  projectId: "associate-research-services",
  storageBucket: "associate-research-services.firebasestorage.app",
  messagingSenderId: "586114194507",
  appId: "1:586114194507:web:e2acb5becbd4d0fbc381ce",
  measurementId: "G-HKDT7YE36Q"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
googleProvider.addScope('email');
googleProvider.addScope('profile');

export default app;
