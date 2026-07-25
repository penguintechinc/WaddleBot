import { useState, useEffect, useCallback } from 'react';
import { superAdminApi } from '../../services/api';

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

const platformLabel = (p) => PLATFORM_OPTIONS.find((o) => o.value === (p || ''))?.label || p;

function SuperAdminFeatureFlags() {
  const [tab, setTab] = useState('flags');

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold gradient-text">Feature Flags</h1>
      </div>

      <div className="flex gap-2 mb-6 border-b border-navy-700">
        <button
          onClick={() => setTab('flags')}
          className={`pb-3 px-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'flags' ? 'border-gold-400 text-gold-400' : 'border-transparent text-navy-400 hover:text-sky-300'
          }`}
        >
          Global Flags
        </button>
        <button
          onClick={() => setTab('audit')}
          className={`pb-3 px-2 text-sm font-medium border-b-2 transition-colors ${
            tab === 'audit' ? 'border-gold-400 text-gold-400' : 'border-transparent text-navy-400 hover:text-sky-300'
          }`}
        >
          Audit Trail
        </button>
      </div>

      {tab === 'flags' ? <GlobalFlagsTab /> : <AuditTab />}
    </div>
  );
}

function GlobalFlagsTab() {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [editModal, setEditModal] = useState(null); // { mode, flag }

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = {};
      if (search) params.search = search;
      const res = await superAdminApi.getFeatureFlags(params);
      if (res.data.success) setFlags(res.data.flags || []);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load feature flags');
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => { load(); }, [load]);

  const handleToggle = async (flag) => {
    try {
      await superAdminApi.updateFeatureFlag(flag.id, { is_enabled: !flag.is_enabled });
      load();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to toggle flag');
    }
  };

  const handleDelete = async (flag) => {
    if (!confirm(`Delete global flag "${flag.flag_key}"? Community overrides are not removed.`)) return;
    try {
      await superAdminApi.deleteFeatureFlag(flag.id);
      load();
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to delete flag');
    }
  };

  return (
    <div>
      <div className="card p-4 mb-6 flex flex-wrap gap-4 items-center">
        <input
          type="text"
          placeholder="Search flag key or description..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input flex-1 min-w-[220px]"
        />
        <button onClick={() => setEditModal({ mode: 'create', flag: null })} className="btn btn-primary">
          + New Global Flag
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 mb-6">{error}</div>
      )}

      <div className="card overflow-hidden">
        <table>
          <thead>
            <tr>
              <th>Flag Key</th>
              <th>Platform</th>
              <th>State</th>
              <th>Rollout %</th>
              <th>Overrides</th>
              <th>Updated By</th>
              <th className="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400 mx-auto"></div>
                </td>
              </tr>
            ) : flags.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-navy-400">No global feature flags defined</td>
              </tr>
            ) : (
              flags.map((flag) => (
                <tr key={flag.id}>
                  <td>
                    <div className="font-mono text-sm text-sky-100">{flag.flag_key}</div>
                    {flag.description && <div className="text-xs text-navy-400 max-w-xs truncate">{flag.description}</div>}
                  </td>
                  <td>
                    <span className="badge badge-gray text-navy-300">{platformLabel(flag.platform)}</span>
                  </td>
                  <td>
                    <button
                      onClick={() => handleToggle(flag)}
                      className={`badge ${flag.is_enabled ? 'badge-green' : 'badge-red'}`}
                    >
                      {flag.is_enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </td>
                  <td className="text-sky-100">{flag.rollout_pct}%</td>
                  <td>
                    <span className="badge badge-gray text-navy-300">{flag.override_count}</span>
                  </td>
                  <td className="text-sm text-navy-400">{flag.updated_by || '—'}</td>
                  <td className="text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setEditModal({ mode: 'edit', flag })} className="text-sky-400 hover:text-sky-300 text-sm">
                        Edit
                      </button>
                      <button onClick={() => handleDelete(flag)} className="text-red-400 hover:text-red-300 text-sm">
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {editModal && (
        <GlobalFlagModal
          mode={editModal.mode}
          flag={editModal.flag}
          onClose={() => setEditModal(null)}
          onSaved={() => { setEditModal(null); load(); }}
        />
      )}
    </div>
  );
}

function GlobalFlagModal({ mode, flag, onClose, onSaved }) {
  const editing = mode === 'edit';
  const [form, setForm] = useState({
    flag_key: flag?.flag_key || '',
    platform: flag?.platform || '',
    is_enabled: flag ? Boolean(flag.is_enabled) : false,
    rollout_pct: flag?.rollout_pct ?? 100,
    description: flag?.description || '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (!editing && !/^[a-z0-9_.-]+$/.test(form.flag_key)) {
      setError('flag_key may only contain lowercase letters, digits, dot, dash and underscore');
      return;
    }
    const pct = Number(form.rollout_pct);
    if (!Number.isInteger(pct) || pct < 0 || pct > 100) {
      setError('rollout_pct must be an integer between 0 and 100');
      return;
    }
    try {
      setSaving(true);
      if (editing) {
        await superAdminApi.updateFeatureFlag(flag.id, {
          is_enabled: form.is_enabled,
          rollout_pct: pct,
          description: form.description || null,
        });
      } else {
        await superAdminApi.createFeatureFlag({
          flag_key: form.flag_key,
          platform: form.platform || null,
          is_enabled: form.is_enabled,
          rollout_pct: pct,
          description: form.description || null,
        });
      }
      onSaved();
    } catch (err) {
      setError(
        err.response?.data?.error?.message
        || err.response?.data?.error?.details?.[0]?.msg
        || 'Failed to save flag'
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-navy-900 rounded-xl shadow-xl max-w-md w-full mx-4 border border-navy-700">
        <div className="p-6 border-b border-navy-700">
          <h2 className="text-xl font-semibold text-sky-100">{editing ? 'Edit Global Flag' : 'New Global Flag'}</h2>
        </div>
        <form onSubmit={submit}>
          <div className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">{error}</div>
            )}
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Flag Key</label>
              <input
                type="text"
                value={form.flag_key}
                onChange={(e) => setForm({ ...form, flag_key: e.target.value })}
                disabled={editing}
                className="input w-full font-mono text-sm disabled:opacity-60"
                placeholder="my_feature.key"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Platform</label>
              <select
                value={form.platform}
                onChange={(e) => setForm({ ...form, platform: e.target.value })}
                disabled={editing}
                className="input w-full disabled:opacity-60"
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
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                rows={2}
                className="input w-full"
              />
            </div>
            <label className="flex items-center gap-2 text-sky-200">
              <input
                type="checkbox"
                checked={form.is_enabled}
                onChange={(e) => setForm({ ...form, is_enabled: e.target.checked })}
                className="w-4 h-4 rounded bg-navy-800 border-navy-600"
              />
              <span className="text-sm">Enabled globally</span>
            </label>
          </div>
          <div className="p-6 border-t border-navy-700 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function AuditTab() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [flagKey, setFlagKey] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ total: 0, totalPages: 0 });

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, limit: 25 };
      if (flagKey) params.flag_key = flagKey;
      const res = await superAdminApi.getFeatureFlagAudit(params);
      if (res.data.success) {
        setEntries(res.data.entries || []);
        setPagination(res.data.pagination || { total: 0, totalPages: 0 });
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load audit trail');
    } finally {
      setLoading(false);
    }
  }, [page, flagKey]);

  useEffect(() => { load(); }, [load]);

  const actionBadge = (action) => {
    const cls = action === 'created' ? 'badge-green' : action === 'deleted' ? 'badge-red' : 'badge-gray';
    return <span className={`badge ${cls}`}>{action}</span>;
  };

  return (
    <div>
      <div className="card p-4 mb-6 flex flex-wrap gap-4 items-center">
        <input
          type="text"
          placeholder="Filter by exact flag key..."
          value={flagKey}
          onChange={(e) => { setFlagKey(e.target.value); setPage(1); }}
          className="input flex-1 min-w-[220px] font-mono text-sm"
        />
      </div>

      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 mb-6">{error}</div>
      )}

      <div className="card overflow-hidden">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>Flag Key</th>
              <th>Scope</th>
              <th>Changed By</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400 mx-auto"></div>
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-navy-400">No audit entries</td>
              </tr>
            ) : (
              entries.map((entry) => (
                <tr key={entry.id}>
                  <td className="text-sm text-navy-400 whitespace-nowrap">
                    {entry.changed_at ? new Date(entry.changed_at).toLocaleString() : '—'}
                  </td>
                  <td>{actionBadge(entry.action)}</td>
                  <td className="font-mono text-sm text-sky-100">{entry.flag_key}</td>
                  <td className="text-sm text-navy-300">
                    {entry.community_id === null ? 'Global' : `Community #${entry.community_id}`}
                    {entry.platform ? ` · ${platformLabel(entry.platform)}` : ''}
                  </td>
                  <td className="text-sm text-navy-400">{entry.changed_by || '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {pagination.totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-navy-700">
            <div className="text-sm text-navy-400">
              Showing {((page - 1) * 25) + 1} to {Math.min(page * 25, pagination.total)} of {pagination.total}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(pagination.totalPages, p + 1))}
                disabled={page === pagination.totalPages}
                className="btn btn-secondary text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default SuperAdminFeatureFlags;
