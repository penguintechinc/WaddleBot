import { useState, useEffect } from 'react';
import { superAdminApi } from '../../services/api';

const TIER_COLORS = {
  exceptional: 'bg-emerald-500',
  very_good: 'bg-sky-500',
  good: 'bg-gold-500',
  fair: 'bg-orange-500',
  poor: 'bg-red-500',
};

const ACTIVITY_COLORS = [
  'bg-emerald-500',
  'bg-sky-500',
  'bg-gold-500',
  'bg-orange-500',
  'bg-navy-600',
];

function SuperAdminAnalytics() {
  const [overview, setOverview] = useState(null);
  const [growth, setGrowth] = useState(null);
  const [activity, setActivity] = useState(null);
  const [growthPeriod, setGrowthPeriod] = useState('90d');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  useEffect(() => {
    loadGrowth();
  }, [growthPeriod]);

  const loadAll = async () => {
    try {
      setLoading(true);
      const [overviewRes, growthRes, activityRes] = await Promise.all([
        superAdminApi.getAnalytics(),
        superAdminApi.getGrowthTrends({ period: growthPeriod }),
        superAdminApi.getActivityBreakdown(),
      ]);
      if (overviewRes.data.success) setOverview(overviewRes.data);
      if (growthRes.data.success) setGrowth(growthRes.data);
      if (activityRes.data.success) setActivity(activityRes.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  const loadGrowth = async () => {
    try {
      const res = await superAdminApi.getGrowthTrends({ period: growthPeriod });
      if (res.data.success) setGrowth(res.data);
    } catch {
      // silent — overview already loaded
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

  const { summary, reputationTiers, platformBreakdown, communityTypes } = overview || {};
  const maxPlatformCount = Math.max(...(platformBreakdown || []).map(p => p.count), 1);
  const maxTypeCount = Math.max(...(communityTypes || []).map(t => t.count), 1);
  const totalTierUsers = (reputationTiers || []).reduce((s, t) => s + t.count, 0) || 1;

  return (
    <div>
      <h1 className="text-2xl font-bold gradient-text mb-6">Platform Analytics</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card p-6 border-l-4 border-l-sky-400">
          <div className="text-sm text-navy-400 mb-1">Total Users</div>
          <div className="text-3xl font-bold text-sky-100">{summary?.totalUsers?.toLocaleString() || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-emerald-400">
          <div className="text-sm text-navy-400 mb-1">Active Users (30d)</div>
          <div className="text-3xl font-bold text-emerald-400">{summary?.activeUsers30d?.toLocaleString() || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-gold-400">
          <div className="text-sm text-navy-400 mb-1">Total Communities</div>
          <div className="text-3xl font-bold text-gold-400">{summary?.totalCommunities?.toLocaleString() || 0}</div>
        </div>
        <div className="card p-6 border-l-4 border-l-purple-400">
          <div className="text-sm text-navy-400 mb-1">Avg Platform Reputation</div>
          <div className="text-3xl font-bold text-purple-400">{summary?.avgPlatformReputation || 0}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Reputation Tier Distribution */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4 text-sky-100">Reputation Tier Distribution</h2>
          <div className="space-y-3">
            {(reputationTiers || []).map(tier => {
              const pct = ((tier.count / totalTierUsers) * 100).toFixed(1);
              return (
                <div key={tier.shortLabel}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-sky-200">{tier.label} ({tier.min}-{tier.max})</span>
                    <span className="text-navy-400">{tier.count} ({pct}%)</span>
                  </div>
                  <div className="w-full bg-navy-800 rounded-full h-3">
                    <div
                      className={`${TIER_COLORS[tier.shortLabel] || 'bg-navy-500'} h-3 rounded-full transition-all`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Platform Breakdown */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4 text-sky-100">Platform Breakdown</h2>
          <div className="space-y-3">
            {(platformBreakdown || []).map(p => (
              <div key={p.platform}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-sky-200 capitalize">{p.platform || 'Unknown'}</span>
                  <span className="text-navy-400">{p.count}</span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-3">
                  <div
                    className="bg-sky-500 h-3 rounded-full transition-all"
                    style={{ width: `${(p.count / maxPlatformCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
            {(!platformBreakdown || platformBreakdown.length === 0) && (
              <p className="text-navy-500 text-sm">No community platforms yet.</p>
            )}
          </div>
        </div>
      </div>

      {/* Growth Trends */}
      <div className="card p-6 mb-8">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-sky-100">User Growth</h2>
          <div className="flex gap-2">
            {['30d', '90d', '1y'].map(p => (
              <button
                key={p}
                onClick={() => setGrowthPeriod(p)}
                className={`px-3 py-1 rounded text-sm ${
                  growthPeriod === p
                    ? 'bg-sky-600 text-white'
                    : 'bg-navy-800 text-navy-400 hover:text-sky-300'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
        {growth?.users?.length > 0 ? (
          <div className="flex items-end gap-1 h-40">
            {(() => {
              const maxCount = Math.max(...growth.users.map(u => u.count), 1);
              return growth.users.map((u, i) => (
                <div
                  key={i}
                  className="flex-1 bg-sky-500/80 hover:bg-sky-400 rounded-t transition-all relative group"
                  style={{ height: `${(u.count / maxCount) * 100}%`, minHeight: '4px' }}
                >
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block bg-navy-700 text-sky-200 text-xs px-2 py-1 rounded whitespace-nowrap">
                    {u.count} users
                  </div>
                </div>
              ));
            })()}
          </div>
        ) : (
          <p className="text-navy-500 text-sm">No growth data for this period.</p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Activity Segments */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4 text-sky-100">Activity Segments</h2>
          {activity?.segments && (
            <>
              {/* Stacked bar */}
              <div className="flex rounded-full h-6 overflow-hidden mb-4">
                {activity.segments.map((seg, i) => {
                  const pct = (seg.count / (activity.total || 1)) * 100;
                  if (pct === 0) return null;
                  return (
                    <div
                      key={seg.key}
                      className={`${ACTIVITY_COLORS[i]} transition-all`}
                      style={{ width: `${pct}%` }}
                      title={`${seg.label}: ${seg.count}`}
                    />
                  );
                })}
              </div>
              <div className="space-y-2">
                {activity.segments.map((seg, i) => (
                  <div key={seg.key} className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                      <div className={`w-3 h-3 rounded-full ${ACTIVITY_COLORS[i]}`} />
                      <span className="text-sky-200">{seg.label}</span>
                    </div>
                    <span className="text-navy-400">{seg.count.toLocaleString()}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Community Type Distribution */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4 text-sky-100">Community Types</h2>
          <div className="space-y-3">
            {(communityTypes || []).map(t => (
              <div key={t.type}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-sky-200 capitalize">{t.type.replace(/_/g, ' ')}</span>
                  <span className="text-navy-400">{t.count}</span>
                </div>
                <div className="w-full bg-navy-800 rounded-full h-3">
                  <div
                    className="bg-gold-500 h-3 rounded-full transition-all"
                    style={{ width: `${(t.count / maxTypeCount) * 100}%` }}
                  />
                </div>
              </div>
            ))}
            {(!communityTypes || communityTypes.length === 0) && (
              <p className="text-navy-500 text-sm">No communities yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SuperAdminAnalytics;
