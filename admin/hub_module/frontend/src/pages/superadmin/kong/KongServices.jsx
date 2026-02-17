import { useState, useEffect } from 'react';
import { kongApi } from '../../../services/api';
import { handleKongError } from '../../../utils/kongErrorHandler';
import { Plus, Edit2, Trash2, Copy } from 'lucide-react';

export default function KongServices() {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [search, setSearch] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingService, setEditingService] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    protocol: 'http',
    host: '',
    port: '80',
    path: '',
    enabled: true,
  });

  useEffect(() => {
    loadServices();
  }, []);

  const loadServices = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await kongApi.getKongServices({ search });
      setServices(response.data.data || []);
    } catch (err) {
      setError(handleKongError(err, 'Failed to load services'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await kongApi.createKongService(formData);
      setSuccess('Service created successfully');
      setShowCreateModal(false);
      resetForm();
      loadServices();
    } catch (err) {
      setError(handleKongError(err, 'Failed to create service'));
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await kongApi.updateKongService(editingService.id, formData);
      setSuccess('Service updated successfully');
      setShowEditModal(false);
      setEditingService(null);
      resetForm();
      loadServices();
    } catch (err) {
      setError(handleKongError(err, 'Failed to update service'));
    }
  };

  const handleDelete = async (serviceId) => {
    if (!confirm('Are you sure you want to delete this service? Related routes will not be deleted.')) return;

    try {
      await kongApi.deleteKongService(serviceId);
      setSuccess('Service deleted successfully');
      loadServices();
    } catch (err) {
      setError(handleKongError(err, 'Failed to delete service'));
    }
  };

  const openEditModal = (service) => {
    setEditingService(service);
    setFormData({
      name: service.name,
      protocol: service.protocol,
      host: service.host,
      port: service.port?.toString() || '80',
      path: service.path || '',
      enabled: service.enabled !== false,
    });
    setShowEditModal(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      protocol: 'http',
      host: '',
      port: '80',
      path: '',
      enabled: true,
    });
  };

  const getServiceUrl = (service) => {
    const port = service.port ? `:${service.port}` : '';
    return `${service.protocol}://${service.host}${port}${service.path || ''}`;
  };

  const filteredServices = services.filter((service) =>
    service.name?.toLowerCase().includes(search.toLowerCase()) ||
    service.host?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      {/* Success/Error Messages */}
      {success && (
        <div className="mb-6 bg-green-900/20 border border-green-500 text-green-400 px-4 py-3 rounded">
          {success}
          <button onClick={() => setSuccess(null)} className="float-right font-bold">×</button>
        </div>
      )}
      {error && (
        <div className="mb-6 bg-red-900/20 border border-red-500 text-red-400 px-4 py-3 rounded">
          {error}
          <button onClick={() => setError(null)} className="float-right font-bold">×</button>
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex justify-between items-center">
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search services by name or host..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              loadServices();
            }}
            className="w-full px-4 py-2 bg-navy-900 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
          />
        </div>
        <button
          onClick={() => {
            resetForm();
            setShowCreateModal(true);
          }}
          className="ml-4 flex items-center gap-2 px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white rounded-lg font-semibold transition-colors"
        >
          <Plus size={20} />
          Create Service
        </button>
      </div>

      {/* Services Grid */}
      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading services...</div>
      ) : filteredServices.length === 0 ? (
        <div className="text-center py-12 text-gray-400">No services found</div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredServices.map((service) => (
            <div key={service.id} className="bg-navy-900 border border-navy-700 rounded-lg p-6 hover:border-navy-600 transition-colors">
              <div className="flex justify-between items-start mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-sky-400 mb-1">{service.name}</h3>
                  <p className="text-gray-400 text-sm font-mono">{getServiceUrl(service)}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => openEditModal(service)}
                    className="p-2 hover:bg-navy-800 rounded-lg transition-colors text-sky-400"
                    title="Edit"
                  >
                    <Edit2 size={18} />
                  </button>
                  <button
                    onClick={() => handleDelete(service.id)}
                    className="p-2 hover:bg-red-900/50 rounded-lg transition-colors text-red-400"
                    title="Delete"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Protocol</span>
                  <p className="text-white font-semibold">{service.protocol.toUpperCase()}</p>
                </div>
                <div>
                  <span className="text-gray-500">Host</span>
                  <p className="text-white font-semibold">{service.host}</p>
                </div>
                <div>
                  <span className="text-gray-500">Port</span>
                  <p className="text-white font-semibold">{service.port || 'default'}</p>
                </div>
                <div>
                  <span className="text-gray-500">Status</span>
                  <p className={`font-semibold ${service.enabled ? 'text-green-400' : 'text-gray-400'}`}>
                    {service.enabled !== false ? 'Enabled' : 'Disabled'}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {(showCreateModal || showEditModal) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-navy-900 border border-navy-700 rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <h2 className="text-2xl font-bold text-sky-400 mb-6">
              {showCreateModal ? 'Create Service' : 'Edit Service'}
            </h2>
            <form onSubmit={showCreateModal ? handleCreate : handleUpdate}>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Service Name *</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    placeholder="e.g., user-api"
                    className="w-full px-4 py-2 bg-navy-800 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">Protocol *</label>
                    <select
                      value={formData.protocol}
                      onChange={(e) => setFormData({ ...formData, protocol: e.target.value })}
                      className="w-full px-4 py-2 bg-navy-800 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
                      required
                    >
                      <option value="http">HTTP</option>
                      <option value="https">HTTPS</option>
                      <option value="grpc">gRPC</option>
                      <option value="grpcs">gRPCS</option>
                      <option value="tcp">TCP</option>
                      <option value="tls">TLS</option>
                      <option value="udp">UDP</option>
                      <option value="ws">WebSocket</option>
                      <option value="wss">WebSocket Secure</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-400 mb-1">Port</label>
                    <input
                      type="number"
                      value={formData.port}
                      onChange={(e) => setFormData({ ...formData, port: e.target.value })}
                      placeholder="80"
                      className="w-full px-4 py-2 bg-navy-800 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Host *</label>
                  <input
                    type="text"
                    value={formData.host}
                    onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                    placeholder="e.g., api.example.com"
                    className="w-full px-4 py-2 bg-navy-800 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-1">Path (optional)</label>
                  <input
                    type="text"
                    value={formData.path}
                    onChange={(e) => setFormData({ ...formData, path: e.target.value })}
                    placeholder="/api/v1"
                    className="w-full px-4 py-2 bg-navy-800 border border-navy-700 rounded-lg text-white focus:outline-none focus:border-sky-500"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="enabled"
                    checked={formData.enabled}
                    onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                    className="w-4 h-4"
                  />
                  <label htmlFor="enabled" className="text-sm text-gray-400">
                    Enable this service
                  </label>
                </div>
              </div>
              <div className="mt-6 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setShowEditModal(false);
                    setEditingService(null);
                    resetForm();
                  }}
                  className="px-4 py-2 bg-navy-800 hover:bg-navy-700 text-white rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-sky-500 hover:bg-sky-600 text-white rounded-lg font-semibold transition-colors"
                >
                  {showCreateModal ? 'Create' : 'Update'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
