import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { CheckIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { joinRequestApi } from '../../services/api';

function AdminJoinRequests() {
  const { communityId } = useParams();
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    fetchRequests();
  }, [communityId]);

  async function fetchRequests() {
    setLoading(true);
    try {
      const res = await joinRequestApi.list(communityId);
      setRequests(res.data?.requests || []);
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to load join requests.');
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(requestId) {
    setActionLoading(requestId + '-approve');
    try {
      await joinRequestApi.approve(communityId, requestId);
      setRequests(prev => prev.filter(r => r.id !== requestId));
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to approve request.');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReject(requestId) {
    setActionLoading(requestId + '-reject');
    try {
      await joinRequestApi.reject(communityId, requestId);
      setRequests(prev => prev.filter(r => r.id !== requestId));
    } catch (err) {
      setError(err?.response?.data?.error || 'Failed to reject request.');
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-sky-100">Join Requests</h1>
        <button onClick={fetchRequests} className="btn btn-secondary text-sm">Refresh</button>
      </div>

      {error && <p className="text-red-400 text-sm mb-4">{error}</p>}

      <div className="card overflow-hidden">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Message</th>
              <th>Requested</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="4" className="p-12 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400 mx-auto" />
                </td>
              </tr>
            ) : requests.length === 0 ? (
              <tr>
                <td colSpan="4" className="p-12 text-center text-navy-400">
                  No pending join requests
                </td>
              </tr>
            ) : (
              requests.map((req) => (
                <tr key={req.id}>
                  <td>
                    <div className="font-medium text-sky-100">{req.username || 'Unknown'}</div>
                    <div className="text-xs text-navy-500">{req.email}</div>
                  </td>
                  <td className="text-sm text-navy-400 max-w-xs">
                    {req.message || <span className="italic text-navy-600">No message</span>}
                  </td>
                  <td className="text-sm text-navy-400">
                    {new Date(req.created_at).toLocaleDateString()}
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleApprove(req.id)}
                        disabled={actionLoading === req.id + '-approve'}
                        className="flex items-center gap-1 px-2.5 py-1.5 bg-green-500/20 border border-green-500/30 text-green-300 rounded-lg hover:bg-green-500/30 text-xs transition-colors disabled:opacity-50"
                      >
                        <CheckIcon className="w-3.5 h-3.5" />
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => handleReject(req.id)}
                        disabled={actionLoading === req.id + '-reject'}
                        className="flex items-center gap-1 px-2.5 py-1.5 bg-red-500/20 border border-red-500/30 text-red-300 rounded-lg hover:bg-red-500/30 text-xs transition-colors disabled:opacity-50"
                      >
                        <XMarkIcon className="w-3.5 h-3.5" />
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default AdminJoinRequests;
