import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { communityApi } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { getPlatformIcon, getPlatformLabel } from '../../utils/platformConfig';

function DashboardHome() {
  const { user, isSuperAdmin, refreshUser } = useAuth();
  const [communities, setCommunities] = useState([]);
  const [loading, setLoading] = useState(true);

  // Refresh user data on mount to ensure role flags (e.g. isSuperAdmin) are current
  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  useEffect(() => {
    async function fetchCommunities() {
      try {
        const response = await communityApi.getMyCommunities();
        setCommunities(response.data.communities);
      } catch (err) {
        console.error('Failed to fetch communities:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchCommunities();
  }, []);

  const roleColor = (role) => {
    switch (role) {
      case 'community-owner': return 'bg-gold-500/20 text-gold-300 border border-gold-500/30';
      case 'community-admin': return 'bg-purple-500/20 text-purple-300 border border-purple-500/30';
      case 'moderator': return 'bg-sky-500/20 text-sky-300 border border-sky-500/30';
      default: return 'bg-navy-700 text-navy-300 border border-navy-600';
    }
  };

  const roleLabel = (role) => {
    return role.replace('community-', '').charAt(0).toUpperCase() + role.replace('community-', '').slice(1);
  };

  return (
    <div>
      {/* Super Admin Banner */}
      {isSuperAdmin && (
        <div className="mb-6 p-4 bg-gradient-to-r from-gold-600 via-gold-500 to-emerald-500 rounded-lg text-navy-950 flex items-center justify-between glow-gold">
          <div>
            <div className="font-semibold">Super Admin Access</div>
            <div className="text-sm text-navy-800">You have global administrative privileges</div>
          </div>
          <Link
            to="/superadmin"
            className="px-4 py-2 bg-navy-900 text-gold-400 rounded-lg font-medium hover:bg-navy-800 transition-colors border border-navy-700"
          >
            Open Control Panel
          </Link>
        </div>
      )}

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-sky-100">Welcome back, {user?.username}!</h1>
        <p className="text-navy-400">Manage your communities and explore activity</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sky-400"></div>
        </div>
      ) : communities.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="mb-4 flex justify-center">
            <img src="/waddlebot-logo.png" alt="Community Logo" className="w-24 h-24" />
          </div>
          <h2 className="text-xl font-semibold mb-2 text-sky-100">No Communities Yet</h2>
          <p className="text-navy-400 mb-6">
            You haven't joined any communities yet. Browse available communities to get started.
          </p>
          <Link to="/communities" className="btn btn-primary">
            Browse Communities
          </Link>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {communities.map((community) => (
            <Link
              key={community.id}
              to={`/dashboard/community/${community.id}`}
              className="card hover:border-sky-500 transition-all overflow-hidden group"
            >
              <div className="aspect-video bg-gradient-to-br from-navy-700 to-navy-800 flex items-center justify-center group-hover:from-sky-900 group-hover:to-navy-800 transition-all">
                {community.logoUrl ? (
                  <img
                    src={community.logoUrl}
                    alt={community.displayName}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <img src="/waddlebot-logo.png" alt="Community Logo" className="w-16 h-16" />
                )}
              </div>
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2 min-w-0">
                    {community.primaryPlatform && (
                      <span title={getPlatformLabel(community.primaryPlatform)}>
                        {getPlatformIcon(community.primaryPlatform)}
                      </span>
                    )}
                    <h3 className="font-semibold truncate text-sky-100">{community.displayName}</h3>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full whitespace-nowrap ${roleColor(community.role)}`}>
                    {roleLabel(community.role)}
                  </span>
                </div>
                <p className="text-sm text-navy-400 line-clamp-2">
                  {community.description || 'No description'}
                </p>
                <div className="mt-3 flex items-center justify-between text-xs text-navy-500">
                  <span>{community.memberCount} members</span>
                  <span>Joined {new Date(community.joinedAt).toLocaleDateString()}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default DashboardHome;
