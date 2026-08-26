import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import { AuthProvider } from './contexts/AuthContext';
import { SocketProvider } from './contexts/SocketContext';
import { CookieConsentProvider } from './contexts/CookieConsentContext';
import CookieBanner from './components/CookieBanner';
import CookiePreferencesModal from './components/CookiePreferencesModal';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <CookieConsentProvider>
      <AuthProvider>
        <SocketProvider>
          <BrowserRouter>
            <App />
            <CookieBanner />
            <CookiePreferencesModal />
          </BrowserRouter>
        </SocketProvider>
      </AuthProvider>
    </CookieConsentProvider>
  </React.StrictMode>
);
