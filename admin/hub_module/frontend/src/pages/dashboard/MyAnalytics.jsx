import { useState, useEffect } from 'react';
import { analyticsApi } from '../../services/api';
import {
  ChatBubbleLeftIcon,
  ClockIcon,
  HomeIcon,
  StarIcon,
} from '@heroicons/react/24/outline';

function MyAnalytics() {
  const [stats, setStats] = useState(null);
  const [reputation, setReputation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsRes, repRes] = await Promise.all([
        analyticsApi.getMyStats(),
        analyticsApi.getMyReputation(),
      ]);
      setStats(statsRes.data);
      setReputation(repRes.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.error || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-400"></div>
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

  const globalRep = reputation?.global_reputation ?? reputation?.globalReputation;
  const communityStats = stats?.communities || [];
  const communityRepList = reputation?.communities || [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-sky-100">My Analytics</h1>
        <p className="text-navy-400 mt-1">Your personal activity and reputation overview</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6 border-l-4 border-l-sky-400">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-navy-400">Total Messages</div>
            <ChatBubbleLeftIcon className="w-5 h-5 text-navy-500" />
          </div>
          <div className="text-3xl font-bold text-sky-100">
            {stats?.total_messages?.toLocaleString() ?? stats?.totalMessages?.toLocaleString() ?? 0}
          </div>
        </div>

        <div className="card p-6 border-l-4 border-l-emerald-400">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-navy-400">Watch Hours</div>
            <ClockIcon className="w-5 h-5 text-navy-500" />
          </div>
          <div className="text-3xl font-bold text-emerald-400">
            {Math.floor((stats?.total_watch_minutes ?? stats?.totalWatchMinutes ?? 0) / 60)}h
          </div>
        </div>

        <div className="card p-6 border-l-4 border-l-gold-400">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-navy-400">Communities</div>
            <HomeIcon className="w-5 h-5 text-navy-500" />
          </div>
          <div className="text-3xl font-bold text-gold-400">
            {stats?.community_count ?? stats?.communityCount ?? communityStats.length}
          </div>
        </div>

        <div className="card p-6 border-l-4 border-l-purple-400">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-navy-400">Global Reputation</div>
            <StarIcon className="w-5 h-5 text-navy-500" />
          </div>
          <div className="text-3xl font-bold text-purple-400">
            {globalRep ?? '—'}
          </div>
        </div>
      </div>

      {/* Per-community Activity Table */}
      {communityStats.length > 0 && (
        <div className="card overflow-hidden mb-8">
          <div className="p-6 pb-0">
            <h2 className="text-lg font-semibold text-sky-100 mb-4">Activity by Community</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-navy-900 border-b border-navy-700">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase">Community</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase">Messages</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase">Watch Hours</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase">Role</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase">Last Active</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-700">
                {communityStats.map((c) => (
                  <tr key={c.id || c.community_id} className="hover:bg-navy-700/50 transition-colors">
                    <td className="px-4 py-3 text-sm text-sky-100 font-medium">
                      {c.name || c.community_name || `Community #${c.id || c.community_id}`}
                    </td>
                    <td className="px-4 py-3 text-sm text-navy-300">
                      {(c.messages ?? c.message_count ?? 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-navy-300">
                      {Math.floor((c.watch_minutes ?? c.watch_hours ?? 0) / (c.watch_hours !== undefined ? 1 : 60))}h
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className="px-2 py-1 bg-navy-700 text-navy-300 rounded text-xs border border-navy-600">
                        {c.role || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-navy-400">
                      {c.last_active || c.lastActive
                        ? new Date(c.last_active || c.lastActive).toLocaleDateString()
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Reputation Card */}
      {reputation && (
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-sky-100 mb-4">Reputation</h2>
          <div className="flex items-center gap-4 mb-6">
            <div className="text-4xl font-bold text-purple-400">{globalRep ?? '—'}</div>
            <div>
              <div className="text-sm text-navy-400">Global Score</div>
              <div className="text-xs text-navy-500">Across all communities</div>
            </div>
          </div>

          {communityRepList.length > 0 && (
            <>
              <h3 className="text-sm font-semibold text-navy-300 mb-3">By Community</h3>
              <div className="space-y-2">
                {communityRepList.map((c) => (
                  <div key={c.id || c.community_id} className="flex items-center justify-between py-2 border-b border-navy-800 last:border-0">
                    <span className="text-sm text-sky-200">
                      {c.name || c.community_name || `Community #${c.id || c.community_id}`}
                    </span>
                    <span className="text-sm font-semibold text-purple-400">
                      {c.reputation ?? c.score ?? '—'}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default MyAnalytics;
