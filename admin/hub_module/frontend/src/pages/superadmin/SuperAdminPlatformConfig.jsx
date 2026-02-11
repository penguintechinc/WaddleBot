import { useState, useEffect } from 'react';
import { superAdminApi } from '../../services/api';
import { RefreshCw, AlertCircle, Check, X } from 'lucide-react';
import BotCredentialTab from './credentials/BotCredentialTab';
import CommunityOAuthTab from './credentials/CommunityOAuthTab';
import UserOAuthTab from './credentials/UserOAuthTab';
import '../../styles/credentials.css';

export default function SuperAdminPlatformConfig() {
  const [activeTab, setActiveTab] = useState('bot');
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);

  const tabs = [
    { id: 'bot', label: 'Bot Credentials', icon: '🤖', description: 'Manage platform bot tokens and credentials' },
    { id: 'community', label: 'Community OAuth', icon: '👥', description: 'OAuth integrations for communities' },
    { id: 'user', label: 'User OAuth', icon: '👤', description: 'OAuth integrations for users' },
  ];

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    setError(null);
    setSuccess(null);
  };

  const handleSuccess = (message) => {
    setSuccess(message);
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleError = (message) => {
    setError(message);
    setTimeout(() => setError(null), 5000);
  };

  const currentTab = tabs.find(t => t.id === activeTab);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sky-100">
            🔐 Unified Credential Management
          </h1>
          <p className="text-navy-400 mt-1">
            Manage bot credentials and OAuth integrations across all platforms
          </p>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="flex items-center gap-2 px-4 py-2 text-navy-300 hover:bg-navy-700 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center gap-3">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <span className="text-red-400">{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-400" />
          </button>
        </div>
      )}

      {success && (
        <div className="bg-emerald-500/20 border border-emerald-500/30 rounded-lg p-4 flex items-center gap-3">
          <Check className="w-5 h-5 text-emerald-400" />
          <span className="text-emerald-400">{success}</span>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="card overflow-hidden">
        <div className="flex border-b border-navy-700">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleTabChange(tab.id)}
              className={`flex-1 px-6 py-4 text-left transition-all ${
                activeTab === tab.id
                  ? 'border-b-2 border-b-gold-500 bg-navy-800/50'
                  : 'border-b-2 border-b-transparent hover:bg-navy-800/30'
              }`}
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{tab.icon}</span>
                <div>
                  <h3 className={`font-semibold ${activeTab === tab.id ? 'text-gold-400' : 'text-sky-100'}`}>
                    {tab.label}
                  </h3>
                  <p className="text-xs text-navy-400">{tab.description}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      <div className="credential-tab-content">
        {activeTab === 'bot' && (
          <BotCredentialTab
            onSuccess={handleSuccess}
            onError={handleError}
          />
        )}
        {activeTab === 'community' && (
          <CommunityOAuthTab
            onSuccess={handleSuccess}
            onError={handleError}
          />
        )}
        {activeTab === 'user' && (
          <UserOAuthTab
            onSuccess={handleSuccess}
            onError={handleError}
          />
        )}
      </div>

      {/* Info Note */}
      <div className="card p-4 border-l-4 border-l-sky-400">
        <h4 className="font-medium text-sky-300 mb-2">Security Note</h4>
        <p className="text-sm text-sky-400">
          All credentials are encrypted at rest and require authentication to access.
          Environment variables take precedence over stored values. For production deployments,
          consider using environment variables for sensitive credentials.
        </p>
      </div>
    </div>
  );
}
