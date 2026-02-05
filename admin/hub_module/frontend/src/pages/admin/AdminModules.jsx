import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  PuzzlePieceIcon,
  Cog6ToothIcon,
  XMarkIcon,
  CheckIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline';
import { adminApi } from '../../services/api';

function AdminModules() {
  const { communityId } = useParams();
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [actionLoading, setActionLoading] = useState({});

  // Config modal state
  const [configModal, setConfigModal] = useState(null);
  const [configText, setConfigText] = useState('');
  const [configError, setConfigError] = useState(null);
  const [saving, setSaving] = useState(false);

  // Core module warning state
  const [showCoreWarning, setShowCoreWarning] = useState(false);
  const [pendingDisable, setPendingDisable] = useState(null);

  useEffect(() => {
    loadModules();
  }, [communityId]);

  const loadModules = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await adminApi.getModules(communityId);
      setModules(response.data.modules || []);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load modules');
    } finally {
      setLoading(false);
    }
  };

  const toggleModule = async (moduleId, newValue) => {
    try {
      setActionLoading({ ...actionLoading, [moduleId]: true });
      await adminApi.updateModuleConfig(communityId, moduleId, {
        isEnabled: newValue,
      });
      setMessage({ type: 'success', text: `Module ${newValue ? 'enabled' : 'disabled'} successfully` });
      loadModules();
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to toggle module');
    } finally {
      setActionLoading({ ...actionLoading, [moduleId]: false });
    }
  };

  const handleToggleEnabled = (module) => {
    const newValue = !module.isEnabled;
    if (module.isCore && !newValue) {
      // Show warning before disabling core module
      setPendingDisable({ module, newValue });
      setShowCoreWarning(true);
    } else {
      // Proceed directly for non-core or enabling
      toggleModule(module.moduleId, newValue);
    }
  };

  const confirmDisableCore = async () => {
    if (pendingDisable) {
      await toggleModule(pendingDisable.module.moduleId, pendingDisable.newValue);
      setShowCoreWarning(false);
      setPendingDisable(null);
    }
  };

  const openConfigModal = (module) => {
    setConfigModal(module);
    setConfigText(JSON.stringify(module.config || {}, null, 2));
    setConfigError(null);
  };

  const closeConfigModal = () => {
    setConfigModal(null);
    setConfigText('');
    setConfigError(null);
  };

  const handleSaveConfig = async () => {
    // Validate JSON
    let parsedConfig;
    try {
      parsedConfig = JSON.parse(configText);
    } catch (e) {
      setConfigError('Invalid JSON format');
      return;
    }

    try {
      setSaving(true);
      setConfigError(null);
      await adminApi.updateModuleConfig(communityId, configModal.moduleId, {
        config: parsedConfig,
      });
      setMessage({ type: 'success', text: 'Module configuration saved successfully' });
      closeConfigModal();
      loadModules();
    } catch (err) {
      setConfigError(err.response?.data?.error?.message || 'Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      general: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
      moderation: 'bg-red-500/20 text-red-300 border-red-500/30',
      entertainment: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      music: 'bg-pink-500/20 text-pink-300 border-pink-500/30',
      utility: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
      games: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      ai: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    };
    return colors[category?.toLowerCase()] || 'bg-navy-700 text-navy-300 border-navy-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-sky-100">Module Configuration</h1>
        <p className="text-navy-400 mt-1">
          Manage installed modules and their configurations
        </p>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <ExclamationTriangleIcon className="w-5 h-5 text-red-400" />
            <span className="text-red-400">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      )}

      {message && (
        <div className={`rounded-lg p-4 flex items-center justify-between ${
          message.type === 'success'
            ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
            : 'bg-red-500/20 text-red-300 border border-red-500/30'
        }`}>
          <div className="flex items-center space-x-3">
            <CheckIcon className="w-5 h-5" />
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="hover:opacity-75">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Empty State */}
      {modules.length === 0 ? (
        <div className="bg-navy-800 border border-navy-700 rounded-lg p-12 text-center">
          <PuzzlePieceIcon className="w-12 h-12 text-navy-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-sky-100 mb-2">No Modules Installed</h3>
          <p className="text-navy-400">
            Visit the Marketplace to browse and install modules for your community.
          </p>
        </div>
      ) : (
        /* Module List */
        <div className="bg-navy-800 border border-navy-700 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-navy-900">
              <tr>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Module</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Category</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Status</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Installed</th>
                <th className="text-right py-3 px-4 text-navy-400 font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-700">
              {modules.map((module) => (
                <tr key={module.installationId} className="hover:bg-navy-700/50">
                  <td className="py-4 px-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 bg-navy-700 rounded-lg flex items-center justify-center">
                        <PuzzlePieceIcon className="w-5 h-5 text-gold-400" />
                      </div>
                      <div>
                        <div className="flex items-center">
                          <p className="font-medium text-sky-100">{module.displayName || module.name}</p>
                          {module.isCore && (
                            <span className="ml-2 px-2 py-0.5 text-xs rounded bg-gold-500/20 text-gold-400 border border-gold-500/30">
                              Core
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-navy-400 truncate max-w-xs">{module.description}</p>
                      </div>
                    </div>
                  </td>
                  <td className="py-4 px-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getCategoryColor(module.category)}`}>
                      {module.category || 'General'}
                    </span>
                  </td>
                  <td className="py-4 px-4">
                    <button
                      onClick={() => handleToggleEnabled(module)}
                      disabled={actionLoading[module.moduleId]}
                      className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                        module.isEnabled
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30'
                          : 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
                      } disabled:opacity-50`}
                    >
                      {actionLoading[module.moduleId] ? '...' : module.isEnabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </td>
                  <td className="py-4 px-4 text-navy-400 text-sm">
                    {module.installedAt ? new Date(module.installedAt).toLocaleDateString() : 'N/A'}
                  </td>
                  <td className="py-4 px-4 text-right">
                    <button
                      onClick={() => openConfigModal(module)}
                      className="inline-flex items-center space-x-2 px-3 py-2 bg-navy-700 hover:bg-navy-600 text-sky-100 rounded-lg transition-colors"
                    >
                      <Cog6ToothIcon className="w-4 h-4" />
                      <span>Configure</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Core Module Warning Modal */}
      {showCoreWarning && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-navy-800 rounded-lg p-6 max-w-md border border-navy-700">
            <h3 className="text-lg font-bold text-sky-100 mb-4">Disable Core Module?</h3>
            <p className="text-navy-300 mb-4">
              You are about to disable <span className="text-gold-400">{pendingDisable?.module.displayName || pendingDisable?.module.name}</span>,
              a core Waddles module. This may affect community functionality.
            </p>
            <p className="text-navy-400 text-sm mb-6">
              You can use an external service instead, but some features may not work as expected.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowCoreWarning(false)}
                className="px-4 py-2 text-navy-300 hover:bg-navy-700 rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={confirmDisableCore}
                className="px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/30"
              >
                Disable Anyway
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Modal */}
      {configModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-navy-800 border border-navy-700 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-sky-100">
                Configure: {configModal.displayName || configModal.name}
              </h3>
              <button
                onClick={closeConfigModal}
                className="text-navy-400 hover:text-sky-100"
              >
                <XMarkIcon className="w-6 h-6" />
              </button>
            </div>

            <p className="text-navy-400 text-sm mb-4">
              Edit the module configuration below. The configuration must be valid JSON.
            </p>

            {configError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 mb-4 text-red-400 text-sm">
                {configError}
              </div>
            )}

            <textarea
              value={configText}
              onChange={(e) => setConfigText(e.target.value)}
              className="flex-1 w-full bg-navy-900 border border-navy-700 rounded-lg p-4 font-mono text-sm text-sky-100 focus:outline-none focus:border-gold-500 min-h-[300px] resize-none"
              placeholder="{}"
            />

            <div className="flex justify-end space-x-3 mt-4">
              <button
                onClick={closeConfigModal}
                className="px-4 py-2 text-navy-300 hover:text-sky-100"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveConfig}
                disabled={saving}
                className="px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-900 font-medium rounded-lg disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminModules;
