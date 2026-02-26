import { useState, useEffect, useCallback } from 'react';
import { superadminTenantApi } from '../../services/api';

const LIMIT = 25;

function SuperAdminTenants() {
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ total: 0, totalPages: 0 });
  const [createModal, setCreateModal] = useState(false);
  const [editingTenant, setEditingTenant] = useState(null);
  const [deleteModal, setDeleteModal] = useState(null);

  const loadTenants = useCallback(async () => {
    try {
      setLoading(true);
      const params = { page, limit: LIMIT };
      if (search) params.search = search;

      const response = await superadminTenantApi.getTenants(params);
      if (response.data.success) {
        setTenants(response.data.tenants);
        setPagination(response.data.pagination);
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    loadTenants();
  }, [loadTenants]);

  const handleSearch = (e) => {
    e.preventDefault();
    setPage(1);
    loadTenants();
  };

  const handleCreate = async (data) => {
    try {
      const response = await superadminTenantApi.createTenant(data);
      if (response.data.success) {
        setCreateModal(false);
        loadTenants();
      }
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to create tenant');
    }
  };

  const handleUpdate = async (id, data) => {
    try {
      const response = await superadminTenantApi.updateTenant(id, data);
      if (response.data.success) {
        setEditingTenant(null);
        loadTenants();
      }
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to update tenant');
    }
  };

  const handleDeactivate = async (id) => {
    try {
      const response = await superadminTenantApi.deactivateTenant(id);
      if (response.data.success) {
        setDeleteModal(null);
        loadTenants();
      }
    } catch (err) {
      alert(err.response?.data?.error?.message || 'Failed to deactivate tenant');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-sky-100">Manage Tenants</h1>
        <button
          onClick={() => setCreateModal(true)}
          className="btn btn-primary"
        >
          + Create Tenant
        </button>
      </div>

      {/* Search */}
      <div className="card p-4 mb-6">
        <form onSubmit={handleSearch} className="flex gap-4">
          <input
            type="text"
            placeholder="Search tenants..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input flex-1"
          />
          <button type="submit" className="btn btn-secondary">Search</button>
        </form>
      </div>

      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 mb-6">
          {error}
        </div>
      )}

      {/* Tenants Table */}
      <div className="bg-navy-800 rounded-xl border border-navy-700 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-navy-700">
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Slug</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Display Name</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Type</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Status</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Seat Limit</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-left">Created</th>
              <th className="text-navy-400 text-xs uppercase px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="p-8 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400 mx-auto"></div>
                </td>
              </tr>
            ) : tenants.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-8 text-center text-navy-400">
                  No tenants found
                </td>
              </tr>
            ) : (
              tenants.map((tenant) => (
                <tr
                  key={tenant.id}
                  className="border-b border-navy-700 hover:bg-navy-700/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="font-mono text-sm text-sky-200">{tenant.slug}</span>
                  </td>
                  <td className="px-4 py-3 font-medium text-sky-100">
                    {tenant.displayName}
                  </td>
                  <td className="px-4 py-3">
                    {tenant.isGlobal ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gold-500/20 text-gold-400">
                        Global
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-navy-700 text-navy-400">
                        Standard
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {tenant.isActive ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-500/20 text-green-400">
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-500/20 text-red-400">
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-sm text-navy-300">
                    {tenant.seatLimit ?? <span className="text-navy-500">Unlimited</span>}
                  </td>
                  <td className="px-4 py-3 text-sm text-navy-400">
                    {new Date(tenant.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => setEditingTenant(tenant)}
                        className="text-sky-400 hover:text-sky-300 text-sm"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteModal(tenant)}
                        disabled={tenant.isGlobal}
                        className="text-red-400 hover:text-red-300 text-sm disabled:opacity-30 disabled:cursor-not-allowed"
                        title={tenant.isGlobal ? 'Cannot deactivate global tenant' : 'Deactivate tenant'}
                      >
                        Deactivate
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {pagination.totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t border-navy-700">
            <div className="text-sm text-navy-400">
              Showing {((page - 1) * LIMIT) + 1} to {Math.min(page * LIMIT, pagination.total)} of {pagination.total}
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

      {/* Create Modal */}
      {createModal && (
        <CreateTenantModal
          onClose={() => setCreateModal(false)}
          onCreate={handleCreate}
        />
      )}

      {/* Edit Modal */}
      {editingTenant && (
        <EditTenantModal
          tenant={editingTenant}
          onClose={() => setEditingTenant(null)}
          onSave={handleUpdate}
        />
      )}

      {/* Deactivate Modal */}
      {deleteModal && (
        <DeactivateTenantModal
          tenant={deleteModal}
          onClose={() => setDeleteModal(null)}
          onDeactivate={handleDeactivate}
        />
      )}
    </div>
  );
}

function CreateTenantModal({ onClose, onCreate }) {
  const [form, setForm] = useState({
    slug: '',
    displayName: '',
    description: '',
    seatLimit: '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.slug.trim() || !form.displayName.trim()) {
      alert('Slug and display name are required');
      return;
    }
    setSaving(true);
    await onCreate({
      ...form,
      seatLimit: form.seatLimit !== '' ? parseInt(form.seatLimit, 10) : null,
    });
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-navy-900 rounded-xl shadow-xl max-w-md w-full mx-4 border border-navy-700">
        <div className="p-6 border-b border-navy-700">
          <h2 className="text-xl font-semibold text-sky-100">Create Tenant</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">
                Slug <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, '') })}
                className="input w-full font-mono"
                placeholder="my-tenant"
                required
              />
              <p className="text-xs text-navy-400 mt-1">Lowercase letters, numbers, and hyphens only</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">
                Display Name <span className="text-red-400">*</span>
              </label>
              <input
                type="text"
                value={form.displayName}
                onChange={(e) => setForm({ ...form, displayName: e.target.value })}
                className="input w-full"
                placeholder="My Tenant"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="input w-full"
                rows={3}
                placeholder="Optional description"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Seat Limit</label>
              <input
                type="number"
                value={form.seatLimit}
                onChange={(e) => setForm({ ...form, seatLimit: e.target.value })}
                className="input w-full"
                placeholder="Leave blank for unlimited"
                min="1"
              />
            </div>
          </div>
          <div className="p-6 border-t border-navy-700 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Creating...' : 'Create Tenant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditTenantModal({ tenant, onClose, onSave }) {
  const [form, setForm] = useState({
    displayName: tenant.displayName || '',
    description: tenant.description || '',
    isActive: tenant.isActive,
    seatLimit: tenant.seatLimit ?? '',
    logoUrl: tenant.logoUrl || '',
  });
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    await onSave(tenant.id, {
      ...form,
      seatLimit: form.seatLimit !== '' ? parseInt(form.seatLimit, 10) : null,
    });
    setSaving(false);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-navy-900 rounded-xl shadow-xl max-w-md w-full mx-4 border border-navy-700">
        <div className="p-6 border-b border-navy-700">
          <h2 className="text-xl font-semibold text-sky-100">Edit Tenant</h2>
          <p className="text-sm text-navy-400 mt-1 font-mono">{tenant.slug}</p>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Display Name</label>
              <input
                type="text"
                value={form.displayName}
                onChange={(e) => setForm({ ...form, displayName: e.target.value })}
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="input w-full"
                rows={3}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Logo URL</label>
              <input
                type="url"
                value={form.logoUrl}
                onChange={(e) => setForm({ ...form, logoUrl: e.target.value })}
                className="input w-full"
                placeholder="https://example.com/logo.png"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-sky-200 mb-1">Seat Limit</label>
              <input
                type="number"
                value={form.seatLimit}
                onChange={(e) => setForm({ ...form, seatLimit: e.target.value })}
                className="input w-full"
                placeholder="Leave blank for unlimited"
                min="1"
              />
            </div>
            <label className="flex items-center gap-2 text-sky-200 cursor-pointer">
              <input
                type="checkbox"
                checked={form.isActive}
                onChange={(e) => setForm({ ...form, isActive: e.target.checked })}
                className="w-4 h-4 rounded bg-navy-800 border-navy-600"
              />
              <span className="text-sm">Active</span>
            </label>
          </div>
          <div className="p-6 border-t border-navy-700 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeactivateTenantModal({ tenant, onClose, onDeactivate }) {
  const [confirmSlug, setConfirmSlug] = useState('');
  const [deactivating, setDeactivating] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (confirmSlug !== tenant.slug) {
      alert('Tenant slug does not match');
      return;
    }
    setDeactivating(true);
    await onDeactivate(tenant.id);
    setDeactivating(false);
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="bg-navy-900 rounded-xl shadow-xl max-w-md w-full mx-4 border border-navy-700">
        <div className="p-6 border-b border-navy-700">
          <h2 className="text-xl font-semibold text-red-400">Deactivate Tenant</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="p-6 space-y-4">
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
              This will deactivate the tenant and suspend access for all its members.
            </div>
            <p className="text-sky-100">
              To confirm, type the tenant slug:{' '}
              <strong className="text-red-400">{tenant.slug}</strong>
            </p>
            <input
              type="text"
              value={confirmSlug}
              onChange={(e) => setConfirmSlug(e.target.value)}
              className="input w-full font-mono"
              placeholder="Type tenant slug to confirm"
            />
          </div>
          <div className="p-6 border-t border-navy-700 flex justify-end gap-3">
            <button type="button" onClick={onClose} className="btn btn-secondary">
              Cancel
            </button>
            <button
              type="submit"
              disabled={deactivating || confirmSlug !== tenant.slug}
              className="btn btn-danger disabled:opacity-50"
            >
              {deactivating ? 'Deactivating...' : 'Deactivate Tenant'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SuperAdminTenants;
