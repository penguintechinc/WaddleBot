import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ServerStackIcon,
  CheckCircleIcon,
  XCircleIcon,
  ArrowRightIcon,
} from '@heroicons/react/24/outline';
import { adminApi } from '../../services/api';
import { getPlatformConfig } from '../../utils/platformConfig';

function AdminConnectedPlatforms() {
  const { communityId } = useParams();
  const [platforms, setPlatforms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadPlatforms();
  }, [communityId]);

  const loadPlatforms = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await adminApi.getConnectedPlatforms(communityId);
      setPlatforms(response.data.connectedPlatforms || []);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'Failed to load connected platforms');
    } finally {
      setLoading(false);
    }
  };

  const getPlatformInfo = (platformId) => {
    const cfg = getPlatformConfig(platformId);
    return { name: cfg.label, icon: cfg.icon, color: cfg.color };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-sky-100">Connected Platforms</h1>
        <p className="text-navy-400 mt-1">
          Overview of all platforms connected to your community
        </p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <span className="text-red-400">{error}</span>
        </div>
      )}

      {/* Platform Grid */}
      {platforms.length === 0 ? (
        <div className="bg-navy-800 border border-navy-700 rounded-lg p-12 text-center">
          <ServerStackIcon className="w-12 h-12 text-navy-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-sky-100 mb-2">No Platforms Connected</h3>
          <p className="text-navy-400 mb-4">
            Link your first server to get started.
          </p>
          <Link
            to={`/admin/${communityId}/servers`}
            className="inline-flex items-center space-x-2 px-4 py-2 bg-gold-500 hover:bg-gold-600 text-navy-900 font-medium rounded-lg transition-colors"
          >
            <span>Go to Linked Servers</span>
            <ArrowRightIcon className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {platforms.map((platform) => {
              const info = getPlatformInfo(platform.platform);
              return (
                <div
                  key={platform.platform}
                  className="bg-navy-800 border border-navy-700 rounded-lg p-6 hover:border-navy-600 transition-colors"
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center space-x-3">
                      <span className="text-3xl">{info.icon}</span>
                      <div>
                        <h3 className="font-semibold text-sky-100">{info.name}</h3>
                        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium border ${info.color}`}>
                          {platform.platform}
                        </span>
                      </div>
                    </div>
                    {platform.isActive ? (
                      <CheckCircleIcon className="w-6 h-6 text-green-400" />
                    ) : (
                      <XCircleIcon className="w-6 h-6 text-red-400" />
                    )}
                  </div>

                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-navy-400 text-sm">Linked Servers</span>
                      <span className="text-gold-400 font-semibold text-lg">{platform.serverCount}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-navy-400 text-sm">Status</span>
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        platform.isActive
                          ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                          : 'bg-red-500/20 text-red-400 border border-red-500/30'
                      }`}>
                        {platform.isActive ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Summary Card */}
          <div className="bg-navy-800 border border-navy-700 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-sky-100">Platform Summary</h3>
                <p className="text-navy-400 text-sm mt-1">
                  {platforms.length} platform{platforms.length !== 1 ? 's' : ''} connected with{' '}
                  {platforms.reduce((sum, p) => sum + p.serverCount, 0)} total server{platforms.reduce((sum, p) => sum + p.serverCount, 0) !== 1 ? 's' : ''}
                </p>
              </div>
              <Link
                to={`/admin/${communityId}/servers`}
                className="inline-flex items-center space-x-2 px-4 py-2 bg-navy-700 hover:bg-navy-600 text-sky-100 rounded-lg transition-colors"
              >
                <span>Manage Servers</span>
                <ArrowRightIcon className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default AdminConnectedPlatforms;
