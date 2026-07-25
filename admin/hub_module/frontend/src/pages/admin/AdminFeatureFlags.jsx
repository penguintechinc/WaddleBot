import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  FlagIcon,
  XMarkIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  PencilSquareIcon,
  PlusIcon,
  ArrowUturnLeftIcon,
} from '@heroicons/react/24/outline';
import { adminApi } from '../../services/api';

const PLATFORM_OPTIONS = [
  { value: '', label: 'All platforms' },
  { value: 'twitch', label: 'Twitch' },
  { value: 'discord', label: 'Discord' },
  { value: 'slack', label: 'Slack' },
  { value: 'youtube', label: 'YouTube' },
  { value: 'kick', label: 'Kick' },
  { value: 'teams', label: 'Teams' },
  { value: 'mattermost', label: 'Mattermost' },
  { value: 'googlechat', label: 'Google Chat' },
];

function AdminFeatureFlags() {
  const { communityId } = useParams();
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState({});
  const [editModal, setEditModal] = useState(null); // { mode: 'create'|'edit', flag }

  useEffect(() => {
    loadFlags();
  }, [communityId]);

  const loadFlags = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await adminApi.getFeatureFlags(communityId);
      setFlags(res.data.flags || []);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load feature flags');
    } finally {
      setLoading(false);
    }
  };

  const rowKey = (f) => `${f.flag_key}::${f.platform || '*'}`;

  const toggleEffective = async (flag) => {
    const key = rowKey(flag);
    try {
      setBusy((b) => ({ ...b, [key]: true }));
      if (flag.override_id) {
        // An override exists at exactly this (flag, platform) — update it.
        await adminApi.updateFeatureFlagOverride(communityId, flag.override_id, {
          is_enabled: !flag.effective_enabled,
        });
      } else {
        // No exact override here — the effective state comes from a broader
        // community override or a global row. Create a platform-exact override,
        // the most specific scope, so it always wins the router's resolution.
        await adminApi.createFeatureFlagOverride(communityId, {
          flag_key: flag.flag_key,
          platform: flag.platform || null,
          is_enabled: !flag.effective_enabled,
          rollout_pct: flag.effective_rollout_pct ?? 100,
          description: flag.description || null,
        });
      }
      setMessage({ type: 'success', text: 'Flag updated for this community' });
      loadFlags();
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to update flag');
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const revertOverride = async (flag) => {
    if (!flag.override_id) return;
    if (!confirm('Remove this community override? The next most specific flag (a broader community override or the global default) will take effect.')) return;
    const key = rowKey(flag);
    try {
      setBusy((b) => ({ ...b, [key]: true }));
      await adminApi.deleteFeatureFlagOverride(communityId, flag.override_id);
      setMessage({ type: 'success', text: 'Override removed — the next most specific flag now applies' });
      loadFlags();
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to remove override');
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  };

  const platformLabel = (p) => PLATFORM_OPTIONS.find((o) => o.value === (p || ''))?.label || p;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sky-100">Feature Flags</h1>
          <p className="text-navy-400 mt-1">
            Override global feature flags for this community. Overrides only affect this community.
          </p>
        </div>
        <button
          onClick={() => setEditModal({ mode: 'create', flag: null })}
          className="inline-flex items-center gap-2 px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-900 font-medium rounded-lg"
        >
          <PlusIcon className="w-5 h-5" />
          New Override
        </button>
      </div>

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
        <div className="rounded-lg p-4 flex items-center justify-between bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          <div className="flex items-center space-x-3">
            <CheckIcon className="w-5 h-5" />
            <span>{message.text}</span>
          </div>
          <button onClick={() => setMessage(null)} className="hover:opacity-75">
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
        </div>
      ) : flags.length === 0 ? (
        <div className="bg-navy-800 border border-navy-700 rounded-lg p-12 text-center">
          <FlagIcon className="w-12 h-12 text-navy-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-sky-100 mb-2">No Feature Flags</h3>
          <p className="text-navy-400">
            No global feature flags are defined yet. New overrides you create will appear here.
          </p>
        </div>
      ) : (
        <div className="bg-navy-800 border border-navy-700 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-navy-900">
              <tr>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Flag</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Platform</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Effective State</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Rollout %</th>
                <th className="text-left py-3 px-4 text-navy-400 font-medium text-sm">Source</th>
                <th className="text-right py-3 px-4 text-navy-400 font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-700">
              {flags.map((flag) => {
                const key = rowKey(flag);
                return (
                  <tr key={key} className="hover:bg-navy-700/50">
                    <td className="py-4 px-4">
                      <div className="flex items-center space-x-3">
                        <div className="w-9 h-9 bg-navy-700 rounded-lg flex items-center justify-center">
                          <FlagIcon className="w-5 h-5 text-gold-400" />
                        </div>
                        <div>
                          <p className="font-medium text-sky-100 font-mono text-sm">{flag.flag_key}</p>
                          {flag.description && (
                            <p className="text-sm text-navy-400 truncate max-w-md">{flag.description}</p>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <span className="px-2 py-1 rounded-full text-xs font-medium border bg-navy-700 text-navy-300 border-navy-600">
                        {platformLabel(flag.platform)}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      <button
                        onClick={() => toggleEffective(flag)}
                        disabled={busy[key]}
                        className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                          flag.effective_enabled
                            ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30'
                            : 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
                        } disabled:opacity-50`}
                      >
                        {busy[key] ? '...' : flag.effective_enabled ? 'Enabled' : 'Disabled'}
                      </button>
                    </td>
                    <td className="py-4 px-4 text-sky-100 text-sm">{flag.effective_rollout_pct}%</td>
                    <td className="py-4 px-4">
                      {flag.is_override ? (
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-gold-500/20 text-gold-400 border-gold-500/30">
                          {/* Reflect the row that actually won the router's resolution:
                              a platform row can be governed by the community's
                              all-platform override. */}
                          {flag.winning_scope === 'community-all' && flag.platform
                            ? 'Override (all platforms)'
                            : 'Override'}
                        </span>
                      ) : (
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-sky-500/20 text-sky-300 border-sky-500/30">
                          Global default
                        </span>
                      )}
                    </td>
                    <td className="py-4 px-4 text-right space-x-2 whitespace-nowrap">
                      {flag.override_id ? (
                        <>
                          <button
                            onClick={() => setEditModal({ mode: 'edit', flag })}
                            className="inline-flex items-center gap-1 px-3 py-2 bg-navy-700 hover:bg-navy-600 text-sky-100 rounded-lg transition-colors text-sm"
                          >
                            <PencilSquareIcon className="w-4 h-4" />
                            Edit
                          </button>
                          <button
                            onClick={() => revertOverride(flag)}
                            disabled={busy[key]}
                            className="inline-flex items-center gap-1 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors text-sm disabled:opacity-50"
                          >
                            <ArrowUturnLeftIcon className="w-4 h-4" />
                            Revert
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setEditModal({ mode: 'create', flag })}
                          className="inline-flex items-center gap-1 px-3 py-2 bg-navy-700 hover:bg-navy-600 text-sky-100 rounded-lg transition-colors text-sm"
                        >
                          <PencilSquareIcon className="w-4 h-4" />
                          Override
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {editModal && (
        <OverrideModal
          communityId={communityId}
          mode={editModal.mode}
          flag={editModal.flag}
          onClose={() => setEditModal(null)}
          onSaved={(text) => {
            setEditModal(null);
            setMessage({ type: 'success', text });
            loadFlags();
          }}
          onError={(text) => setError(text)}
        />
      )}
    </div>
  );
}

function OverrideModal({ communityId, mode, flag, onClose, onSaved, onError }) {
  // In "edit" mode the override already exists. In "create" mode from a global
  // row, flag_key/platform are seeded and locked. From the "New Override"
  // button (flag === null) all fields are editable.
  const editing = mode === 'edit';
  const seeded = Boolean(flag);
  const [form, setForm] = useState({
    flag_key: flag?.flag_key || '',
    platform: flag?.platform || '',
    is_enabled: flag ? Boolean(flag.effective_enabled) : false,
    rollout_pct: flag?.effective_rollout_pct ?? 100,
    description: flag?.description || '',
  });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!editing) {
      if (!/^[a-z0-9_.-]+$/.test(form.flag_key) || form.flag_key.length === 0 || form.flag_key.length > 100) {
        setFormError('flag_key may only contain lowercase letters, digits, dot, dash and underscore (max 100 chars)');
        return;
      }
    }
    const pct = Number(form.rollout_pct);
    if (!Number.isInteger(pct) || pct < 0 || pct > 100) {
      setFormError('rollout_pct must be an integer between 0 and 100');
      return;
    }

    try {
      setSaving(true);
      if (editing) {
        await adminApi.updateFeatureFlagOverride(communityId, flag.override_id, {
          is_enabled: form.is_enabled,
          rollout_pct: pct,
          description: form.description || null,
        });
        onSaved('Override updated');
      } else {
        await adminApi.createFeatureFlagOverride(communityId, {
          flag_key: form.flag_key,
          platform: form.platform || null,
          is_enabled: form.is_enabled,
          rollout_pct: pct,
          description: form.description || null,
        });
        onSaved('Override created');
      }
    } catch (err) {
      const msg = err.response?.data?.error?.message
        || err.response?.data?.error?.details?.[0]?.msg
        || 'Failed to save override';
      setFormError(msg);
      onError?.(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-navy-900 rounded-xl shadow-xl max-w-md w-full mx-4 border border-navy-700">
        <div className="p-6 border-b border-navy-700 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-sky-100">
            {editing ? 'Edit Override' : 'Create Override'}
          </h2>
          <button onClick={onClose} className="text-navy-400 hover:text-sky-100">
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>
        <form onSubmit={submit}>
          <div className="p-6 space-y-4">
            {formError && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
                {formError}
              </div>
            )}
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Flag Key</label>
              <input
                type="text"
                value={form.flag_key}
                onChange={(e) => setForm({ ...form, flag_key: e.target.value })}
                disabled={editing || seeded}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-700 rounded-lg text-sky-100 font-mono text-sm focus:outline-none focus:border-gold-500 disabled:opacity-60"
                placeholder="my_feature.key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Platform</label>
              <select
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                disabled={editing || seeded}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-700 rounded-lg text-sky-100 focus:outline-none focus:border-gold-500 disabled:opacity-60"
              >
                {PLATFORM_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Rollout %</label>
              <input
                type="number"
                min="0"
                max="100"
                value={form.rollout_pct}
                onChange={(e) => setForm({ ...form, rollout_pct: e.target.value })}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-700 rounded-lg text-sky-100 focus:outline-none focus:border-gold-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 bg-navy-800 border border-navy-700 rounded-lg text-sky-100 focus:outline-none focus:border-gold-500"
              />
            </div>
            <label className="flex items-center gap-2 text-sky-200">
              <input
                type="checkbox"
                checked={form.is_enabled}
                onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })}
                className="w-4 h-4 rounded bg-navy-800 border-navy-600"
              />
              <span className="text-sm">Enabled for this community</span>
            </label>
          </div>
          <div className="p-6 border-t border-navy-700 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="px-4 py-2 text-navy-300 hover:text-sky-100">
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-900 font-medium rounded-lg disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default AdminFeatureFlags;
