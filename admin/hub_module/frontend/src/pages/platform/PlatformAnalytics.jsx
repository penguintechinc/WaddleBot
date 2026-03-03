import { useState, useEffect } from 'react';
import { analyticsApi } from '../../services/api';
import PlatformSummaryCards from '../../components/analytics/PlatformSummaryCards';
import ReputationTierChart from '../../components/analytics/ReputationTierChart';
import PlatformGrowthChart from '../../components/analytics/PlatformGrowthChart';
import ActivitySegmentChart from '../../components/analytics/ActivitySegmentChart';
import CommunityHealthTable from '../../components/analytics/CommunityHealthTable';

function PlatformAnalytics() {
  const [overview, setOverview] = useState(null);
  const [repData, setRepData] = useState(null);
  const [growthData, setGrowthData] = useState(null);
  const [activityData, setActivityData] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [growthPeriod, setGrowthPeriod] = useState('30d');
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
      setError(null);
      const [overviewRes, repRes, growthRes, activityRes, healthRes] = await Promise.all([
        analyticsApi.getPlatformOverview(),
        analyticsApi.getPlatformReputation(),
        analyticsApi.getPlatformGrowth(growthPeriod),
        analyticsApi.getPlatformActivity(),
        analyticsApi.getCommunityHealth(),
      ]);
      setOverview(overviewRes.data);
      setRepData(repRes.data);
      setGrowthData(growthRes.data);
      setActivityData(activityRes.data);
      setHealthData(healthRes.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || err.response?.data?.error || 'Failed to load platform analytics');
    } finally {
      setLoading(false);
    }
  };

  const loadGrowth = async () => {
    if (loading) return;
    try {
      const res = await analyticsApi.getPlatformGrowth(growthPeriod);
      setGrowthData(res.data);
    } catch {
      // silent — rest of data already loaded
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

  // Normalize overview data shape
  const summaryData = overview
    ? {
        total_users: overview.total_users ?? overview.totalUsers ?? overview.summary?.totalUsers,
        active_users_30d: overview.active_users_30d ?? overview.activeUsers30d ?? overview.summary?.activeUsers30d,
        total_communities: overview.total_communities ?? overview.totalCommunities ?? overview.summary?.totalCommunities,
        avg_reputation: overview.avg_reputation ?? overview.avgReputation ?? overview.summary?.avgPlatformReputation,
      }
    : null;

  // Normalize reputation data
  const repNormalized = repData
    ? {
        buckets: repData.buckets || repData.tiers || repData.reputationTiers || [],
        stats: repData.stats || repData.statistics || {},
      }
    : null;

  // Normalize activity data
  const activityNormalized = activityData
    ? {
        active_24h: activityData.active_24h ?? activityData.active24h,
        active_7d: activityData.active_7d ?? activityData.active7d,
        active_30d: activityData.active_30d ?? activityData.active30d,
        active_90d: activityData.active_90d ?? activityData.active90d,
        inactive: activityData.inactive,
      }
    : null;

  // Normalize growth data
  const growthNormalized = growthData
    ? {
        buckets: growthData.buckets || growthData.users?.map((u, i) => ({
          label: u.label || u.date || String(i),
          new_users: u.count || u.new_users || 0,
          new_communities: growthData.communities?.[i]?.count || 0,
        })) || [],
      }
    : null;

  const communities = healthData?.communities || (Array.isArray(healthData) ? healthData : []);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold gradient-text">Platform Analytics</h1>
        <p className="text-navy-400 mt-1">Platform-wide engagement and growth metrics</p>
      </div>

      <PlatformSummaryCards data={summaryData} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <ReputationTierChart data={repNormalized} />
        <ActivitySegmentChart data={activityNormalized} />
      </div>

      <PlatformGrowthChart
        data={growthNormalized}
        period={growthPeriod}
        onPeriodChange={setGrowthPeriod}
      />

      <CommunityHealthTable data={communities} />
    </div>
  );
}

export default PlatformAnalytics;
