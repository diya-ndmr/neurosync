import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const projectId = import.meta.env.VITE_FIREBASE_PROJECT_ID || 'neurosync-d7b3c';
const apiKey = import.meta.env.VITE_FIREBASE_API_KEY;
const appId = import.meta.env.VITE_FIREBASE_APP_ID;

export const firebaseConfigured = Boolean(apiKey && appId);

const firebaseApp = firebaseConfigured
  ? initializeApp({
      apiKey,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || `${projectId}.firebaseapp.com`,
      projectId,
      appId
    })
  : null;

export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null;

export function requireFirebaseAuth() {
  if (!firebaseAuth) {
    throw new Error('Firebase Authentication is not configured for this deployment.');
  }
  return firebaseAuth;
}

export function firebaseErrorMessage(error: unknown): string {
  const code = (error as { code?: string } | null)?.code;
  switch (code) {
    case 'auth/email-already-in-use':
      return 'An account already exists for this email. Sign in or reset its password.';
    case 'auth/invalid-credential':
    case 'auth/user-not-found':
    case 'auth/wrong-password':
      return 'The email or password is incorrect.';
    case 'auth/weak-password':
      return 'Choose a stronger password.';
    case 'auth/invalid-email':
      return 'Enter a valid email address.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a while and try again.';
    case 'auth/network-request-failed':
      return 'Could not reach Firebase. Check your connection and try again.';
    default:
      return error instanceof Error ? error.message : 'Firebase Authentication failed.';
  }
}
