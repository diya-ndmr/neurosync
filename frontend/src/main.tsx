import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { registerSW } from 'virtual:pwa-register';
import { router } from './routes';
import { AuthProvider } from './context/AuthContext';
import { AccessibilityProvider } from './context/AccessibilityContext';
import { PersonalizationProvider } from './context/PersonalizationContext';
import { ToastProvider } from './components/Toast';
import './index.css';

// Register service worker for PWA support
registerSW({ immediate: true });

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <AccessibilityProvider>
        <PersonalizationProvider>
          <ToastProvider>
            <RouterProvider router={router} />
          </ToastProvider>
        </PersonalizationProvider>
      </AccessibilityProvider>
    </AuthProvider>
  </StrictMode>
);
