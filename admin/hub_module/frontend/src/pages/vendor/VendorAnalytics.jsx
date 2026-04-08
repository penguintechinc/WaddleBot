/**
 * Vendor Analytics
 * Overview of vendor analytics — placeholder with stat cards; full dashboard coming in v2.2.x
 */
import { useEffect, useState } from 'react';
import {
  ChartBarSquareIcon,
  ArrowDownTrayIcon,
  CurrencyDollarIcon,
  StarIcon,
  UserGroupIcon,
} from '@heroicons/react/24/outline';
import api from '../../services/api';

function VendorAnalytics() {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadOverview();
  }, []);

  const loadOverview = async () => {
    try {
      const response = await api.get('/vendor/analytics/overview');
      setOverview(response.data);
    } catch {
      // 404 or any error — gracefully show placeholder state
      setOverview(null);
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ icon: Icon, label, value, color = 'blue', subtitle }) => {
    const colorMap = {
      blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      green: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      gold: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
    };
    return (
      <div className={`${colorMap[color]} border rounded-lg p-6`}>
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm font-medium text-navy-300">{label}</p>
            <p className="text-3xl font-bold mt-2">{value}</p>
            {subtitle && <p className="text-xs text-navy-400 mt-1">{subtitle}</p>}
          </div>
          <Icon className="w-8 h-8 opacity-50" />
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Analytics</h1>
        <p className="text-navy-300 mt-1">Track installs, revenue, and ratings across your modules</p>
      </div>

      {/* Stat cards — real data if available, zeros as fallback */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          icon={ArrowDownTrayIcon}
          label="Total Installs"
          value={(overview?.totalInstalls ?? 0).toLocaleString()}
          color="blue"
          subtitle="All modules combined"
        />
        <StatCard
          icon={CurrencyDollarIcon}
          label="Monthly Revenue"
          value={`$${((overview?.monthlyRevenue ?? 0) / 100).toFixed(2)}`}
          color="green"
          subtitle="Current month"
        />
        <StatCard
          icon={StarIcon}
          label="Avg. Rating"
          value={overview?.avgRating != null ? overview.avgRating.toFixed(1) : '—'}
          color="gold"
          subtitle="Across all modules"
        />
        <StatCard
          icon={UserGroupIcon}
          label="Active Users"
          value={(overview?.activeUsers ?? 0).toLocaleString()}
          color="purple"
          subtitle="Last 30 days"
        />
      </div>

      {/* Chart placeholder */}
      <div className="bg-navy-800 border border-navy-700 rounded-lg p-8">
        <div className="flex items-center space-x-3 mb-6">
          <ChartBarSquareIcon className="w-6 h-6 text-sky-400" />
          <h2 className="text-xl font-bold text-white">Install Trends</h2>
        </div>
        <div className="h-48 flex items-center justify-center border border-dashed border-navy-600 rounded-lg">
          <p className="text-navy-500 text-sm">Chart coming soon</p>
        </div>
      </div>

      {/* Coming soon banner */}
      <div className="bg-sky-500/10 border border-sky-500/20 rounded-lg p-6 flex items-start space-x-4">
        <ChartBarSquareIcon className="w-8 h-8 text-sky-400 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="text-sky-400 font-bold text-lg">Analytics Dashboard Coming in v2.2.x</h3>
          <p className="text-navy-300 mt-1 text-sm">
            The full analytics suite — including install trends over time, revenue breakdowns per module,
            geographic distribution, and conversion funnels — is being built out as part of the v2.2.x
            release. Stay tuned!
          </p>
        </div>
      </div>
    </div>
  );
}

export default VendorAnalytics;
