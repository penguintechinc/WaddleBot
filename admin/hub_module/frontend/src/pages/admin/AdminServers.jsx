import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { adminApi } from '../../services/api';
import { getPlatformIcon, getPlatformColor } from '../../utils/platformConfig';

const PLATFORM_ICONS = new Proxy({}, { get: (_, key) => getPlatformIcon(key) });
const PLATFORM_COLORS = new Proxy({}, { get: (_, key) => getPlatformColor(key) });

function AdminServers() {
  const { communityId } = useParams();
  const [servers, setServers] = useState([]);
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('servers');
  const [actionLoading, setActionLoading] = useState(null);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    fetchData();
  }, [communityId]);

  async function fetchData() {
    setLoading(true);
    try {
      const [serversRes, requestsRes] = await Promise.all([
        adminApi.getServers(communityId),
        adminApi.getServerLinkRequests(communityId, { status: 'pending' }),
      ]);
      setServers(serversRes.data.servers || []);
      setRequests(requestsRes.data.requests || []);
    } catch (err) {
      console.error('Failed to fetch servers:', err);
      setMessage({ type: 'error', text: 'Failed to load servers' });
    } finally {
      setLoading(false);
    }
  }

  async function handleApproveRequest(requestId) {
    setActionLoading(requestId);
    try {
      await adminApi.approveServerLinkRequest(communityId, requestId);
      setMessage({ type: 'success', text: 'Server link approved' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error?.message || 'Failed to approve request' });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRejectRequest(requestId) {
    setActionLoading(requestId);
    try {
      await adminApi.rejectServerLinkRequest(communityId, requestId);
      setMessage({ type: 'success', text: 'Server link rejected' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error?.message || 'Failed to reject request' });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRemoveServer(serverId) {
    if (!confirm('Are you sure you want to remove this server?')) return;
    setActionLoading(serverId);
    try {
      await adminApi.removeServer(communityId, serverId);
      setMessage({ type: 'success', text: 'Server removed' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error?.message || 'Failed to remove server' });
    } finally {
      setActionLoading(null);
    }
  }

  async function handleSetPrimary(serverId) {
    setActionLoading(serverId);
    try {
      await adminApi.updateServer(communityId, serverId, { isPrimary: true });
      setMessage({ type: 'success', text: 'Primary server updated' });
      fetchData();
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error?.message || 'Failed to update server' });
    } finally {
      setActionLoading(null);
    }
  }

  const pendingCount = requests.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-sky-100">Linked Servers</h1>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-lg border ${
          message.type === 'success'
            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
            : 'bg-red-500/20 text-red-300 border-red-500/30'
        }`}>
          {message.text}
          <button onClick={() => setMessage(null)} className="float-right">×</button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1 mb-6 bg-navy-800 p-1 rounded-lg w-fit">
        <button
          onClick={() => setActiveTab('servers')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'servers'
              ? 'bg-navy-700 text-sky-100'
              : 'text-navy-400 hover:text-sky-100'
          }`}
        >
          Linked Servers ({servers.length})
        </button>
        <button
          onClick={() => setActiveTab('requests')}
          className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
            activeTab === 'requests'
              ? 'bg-navy-700 text-sky-100'
              : 'text-navy-400 hover:text-sky-100'
          }`}
        >
          Pending Requests
          {pendingCount > 0 && (
            <span className="ml-2 px-2 py-0.5 text-xs bg-gold-400 text-navy-900 rounded-full">
              {pendingCount}
            </span>
          )}
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
        </div>
      ) : activeTab === 'servers' ? (
        /* Linked Servers Tab */
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {servers.length === 0 ? (
            <div className="col-span-full card p-12 text-center">
              <div className="text-4xl mb-4">🔗</div>
              <h3 className="text-lg font-medium text-sky-100 mb-2">No Linked Servers</h3>
              <p className="text-navy-400">
                Platform admins can link their servers to this community.
              </p>
            </div>
          ) : (
            servers.map((server) => (
              <div key={server.id} className="card p-4">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{PLATFORM_ICONS[server.platform] || '🌐'}</span>
                    <div>
                      <h3 className="font-medium text-sky-100">{server.platformServerName}</h3>
                      <span className={`text-xs px-2 py-0.5 rounded border ${PLATFORM_COLORS[server.platform] || 'bg-navy-700'}`}>
                        {server.platform}
                      </span>
                    </div>
                  </div>
                  {server.isPrimary && (
                    <span className="badge badge-gold">Primary</span>
                  )}
                </div>

                <div className="text-xs text-navy-500 mb-3">
                  <div>ID: {server.platformServerId}</div>
                  <div>Added by: {server.addedBy || 'Unknown'}</div>
                  <div>Linked: {new Date(server.createdAt).toLocaleDateString()}</div>
                </div>

                <div className="flex space-x-2">
                  {!server.isPrimary && (
                    <button
                      onClick={() => handleSetPrimary(server.id)}
                      disabled={actionLoading === server.id}
                      className="btn btn-secondary text-xs flex-1 disabled:opacity-50"
                    >
                      Set Primary
                    </button>
                  )}
                  <button
                    onClick={() => handleRemoveServer(server.id)}
                    disabled={actionLoading === server.id}
                    className="btn bg-red-500/20 text-red-300 hover:bg-red-500/30 text-xs disabled:opacity-50"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* Pending Requests Tab */
        <div className="card overflow-hidden">
          {requests.length === 0 ? (
            <div className="p-12 text-center">
              <div className="text-4xl mb-4">✅</div>
              <h3 className="text-lg font-medium text-sky-100 mb-2">No Pending Requests</h3>
              <p className="text-navy-400">
                All server link requests have been processed.
              </p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Server</th>
                  <th>Platform</th>
                  <th>Requested By</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.map((request) => (
                  <tr key={request.id}>
                    <td>
                      <div className="font-medium text-sky-100">{request.platformServerName}</div>
                      <div className="text-xs text-navy-500">{request.platformServerId}</div>
                    </td>
                    <td>
                      <span className={`text-xs px-2 py-1 rounded border ${PLATFORM_COLORS[request.platform] || 'bg-navy-700'}`}>
                        {PLATFORM_ICONS[request.platform]} {request.platform}
                      </span>
                    </td>
                    <td>
                      <div className="text-sky-100">{request.requestedBy}</div>
                      <div className="text-xs text-navy-500">{request.requestedByEmail}</div>
                    </td>
                    <td className="text-sm text-navy-400">
                      {new Date(request.createdAt).toLocaleDateString()}
                    </td>
                    <td>
                      <div className="flex space-x-2">
                        <button
                          onClick={() => handleApproveRequest(request.id)}
                          disabled={actionLoading === request.id}
                          className="btn btn-primary text-xs disabled:opacity-50"
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => handleRejectRequest(request.id)}
                          disabled={actionLoading === request.id}
                          className="btn bg-red-500/20 text-red-300 hover:bg-red-500/30 text-xs disabled:opacity-50"
                        >
                          Reject
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

export default AdminServers;
