import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { superAdminApi } from '../../services/api';

function SuperAdminDashboard() {
  const [stats, setStats] = useState(null);
  const [recentCommunities, setRecentCommunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadDashboard();
  }, []);

  const loadDashboard = async () => {
    try {
      setLoading(true);
      const response = await superAdminApi.getDashboard();
      if (response.data.success) {
        setStats(response.data.stats);
        setRecentCommunities(response.data.recentCommunities || []);
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300">
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold gradient-text">Super Admin Dashboard</h1>
        <Link to="/communities/create" className="btn btn-primary">
          + Create Community
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6 border-l-4 border-l-sky-400">
          <div className="text-sm text-navy-400 mb-1">Total Communities</div>
          <div className="text-3xl font-bold text-sky-100">{stats?.totalCommunities || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-emerald-400">
          <div className="text-sm text-navy-400 mb-1">Active Communities</div>
          <div className="text-3xl font-bold text-emerald-400">{stats?.activeCommunities || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-gold-400">
          <div className="text-sm text-navy-400 mb-1">Total Members</div>
          <div className="text-3xl font-bold text-gold-400">{stats?.totalMembers || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-purple-400">
          <div className="text-sm text-navy-400 mb-1">Active Admins</div>
          <div className="text-3xl font-bold text-purple-400">{stats?.adminCount || 0}</div>
        </div>
      </div>

      {/* Platform Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4 text-sky-100">Platform Breakdown</h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-indigo-400"></span>
                <span className="text-sky-200">Discord</span>
              </div>
              <span className="font-semibold text-sky-100">{stats?.platformBreakdown?.discord || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-purple-400"></span>
                <span className="text-sky-200">Twitch</span>
              </div>
              <span className="font-semibold text-sky-100">{stats?.platformBreakdown?.twitch || 0}</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="w-3 h-3 rounded-full bg-emerald-400"></span>
                <span className="text-sky-200">Slack</span>
              </div>
              <span className="font-semibold text-sky-100">{stats?.platformBreakdown?.slack || 0}</span>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-sky-100">Recent Communities</h2>
            <Link to="/superadmin/communities" className="text-sm text-sky-400 hover:text-sky-300">
              View all
            </Link>
          </div>
          {recentCommunities.length === 0 ? (
            <p className="text-navy-400">No communities yet</p>
          ) : (
            <div className="space-y-3">
              {recentCommunities.map((community) => (
                <Link
                  key={community.id}
                  to={`/superadmin/communities/${community.id}`}
                  className="flex items-center justify-between p-3 bg-navy-800 rounded-lg hover:bg-navy-700 border border-navy-600 hover:border-sky-500 transition-all"
                >
                  <div>
                    <div className="font-medium text-sky-100">{community.displayName}</div>
                    <div className="text-sm text-navy-400">{community.platform}</div>
                  </div>
                  <div className="text-xs text-navy-500">
                    {new Date(community.createdAt).toLocaleDateString()}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4 text-sky-100">Quick Actions</h2>
        <div className="flex flex-wrap gap-3">
          <Link to="/superadmin/communities" className="btn btn-secondary">
            Manage Communities
          </Link>
          <Link to="/superadmin/communities/new" className="btn btn-primary">
            Create Community
          </Link>
        </div>
      </div>
    </div>
  );
}

export default SuperAdminDashboard;
