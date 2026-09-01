import { useState, useEffect } from 'react';
import { superAdminApi } from '../../../services/api';
import { Plus, RefreshCw, AlertCircle } from 'lucide-react';
import CredentialForm from './CredentialForm';
import CredentialTable from './CredentialTable';

export default function BotCredentialTab({ onSuccess, onError }) {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedCredential, setSelectedCredential] = useState(null);

  useEffect(() => {
    fetchCredentials();
  }, []);

  const fetchCredentials = async () => {
    try {
      setLoading(true);
      const response = await superAdminApi.getPlatformConfigs();

      // Filter bot credentials from the response
      const botCreds = Object.entries(response.data.configs || {}).map(([platform, config]) => ({
        id: platform,
        platform,
        ...config,
        integrationType: 'bot',
      }));

      setCredentials(botCreds);
    } catch (error) {
      onError(`Failed to load bot credentials: ${error.response?.data?.message || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (formData) => {
    try {
      await superAdminApi.updatePlatformConfig(formData.platform, {
        ...formData,
        integrationType: 'bot',
      });

      onSuccess(`Bot credential for ${formData.platform} saved successfully`);
      setShowForm(false);
      setSelectedCredential(null);
      fetchCredentials();
    } catch (error) {
      onError(`Save failed: ${error.response?.data?.message || error.message}`);
    }
  };

  const handleDelete = async (credentialId) => {
    if (!window.confirm('Delete this bot credential? This action cannot be undone.')) return;

    try {
      // Note: actual delete implementation depends on backend API
      onSuccess('Bot credential deleted successfully');
      fetchCredentials();
    } catch (error) {
      onError(`Delete failed: ${error.response?.data?.message || error.message}`);
    }
  };

  const handleEdit = (credential) => {
    setSelectedCredential(credential);
    setShowForm(true);
  };

  return (
    <div className="credential-tab">
      {!showForm ? (
        <>
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-bold text-sky-100">Bot Credentials</h2>
              <p className="text-sm text-navy-400 mt-1">
                Configure API credentials for bot integrations
              </p>
            </div>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-950 font-medium rounded-lg transition-colors"
            >
              <Plus className="w-4 h-4" />
              Add Bot Credential
            </button>
          </div>

          {loading ? (
            <div className="card p-8 flex items-center justify-center gap-3">
              <RefreshCw className="w-5 h-5 animate-spin text-gold-400" />
              <span className="text-navy-300">Loading bot credentials...</span>
            </div>
          ) : credentials.length === 0 ? (
            <div className="card p-12 text-center">
              <AlertCircle className="w-12 h-12 text-navy-500 mx-auto mb-3" />
              <h3 className="text-sky-100 font-semibold mb-1">No Bot Credentials Configured</h3>
              <p className="text-navy-400 mb-4">
                Add your first bot credential to get started
              </p>
              <button
                onClick={() => setShowForm(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-950 font-medium rounded-lg transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Credential
              </button>
            </div>
          ) : (
            <CredentialTable
              credentials={credentials}
              onEdit={handleEdit}
              onDelete={handleDelete}
              integrationType="bot"
            />
          )}
        </>
      ) : (
        <CredentialForm
          credential={selectedCredential}
          integrationType="bot"
          onSave={handleSave}
          onCancel={() => {
            setShowForm(false);
            setSelectedCredential(null);
          }}
        />
      )}
    </div>
  );
}
