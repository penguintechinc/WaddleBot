import { Outlet, Link, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  HomeIcon,
  UserGroupIcon,
  PuzzlePieceIcon,
  GlobeAltIcon,
  ChartBarIcon,
  DocumentTextIcon,
  ArrowLeftOnRectangleIcon,
  ShieldCheckIcon,
  Cog6ToothIcon,
  BuildingStorefrontIcon,
  ServerStackIcon,
  RectangleGroupIcon,
  ArrowsRightLeftIcon,
  TrophyIcon,
  ScaleIcon,
  SparklesIcon,
  WindowIcon,
  CurrencyDollarIcon,
  MegaphoneIcon,
  FireIcon,
  CommandLineIcon,
  SpeakerWaveIcon,
  LanguageIcon,
} from '@heroicons/react/24/outline';

function AdminLayout() {
  const { user, logout, isPlatformAdmin, isSuperAdmin } = useAuth();
  const location = useLocation();
  const { communityId } = useParams();

  // Community admin nav
  const communityAdminNav = communityId
    ? [
        { to: `/admin/${communityId}`, icon: HomeIcon, label: 'Overview', exact: true },
        { to: `/admin/${communityId}/members`, icon: UserGroupIcon, label: 'Members' },
        { to: `/admin/${communityId}/announcements`, icon: MegaphoneIcon, label: 'Announcements' },
        { to: `/admin/${communityId}/workflows`, icon: CommandLineIcon, label: 'Workflows', premium: true },
        { to: `/admin/${communityId}/analytics`, icon: ChartBarIcon, label: 'Analytics' },
        { to: `/admin/${communityId}/security`, icon: FireIcon, label: 'Security' },
        { to: `/admin/${communityId}/servers`, icon: ServerStackIcon, label: 'Linked Servers' },
        { to: `/admin/${communityId}/connected-platforms`, icon: RectangleGroupIcon, label: 'Connected Platforms' },
        { to: `/admin/${communityId}/mirror-groups`, icon: ArrowsRightLeftIcon, label: 'Chat Mirroring' },
        { to: `/admin/${communityId}/leaderboard`, icon: TrophyIcon, label: 'Leaderboards' },
        { to: `/admin/${communityId}/reputation`, icon: ScaleIcon, label: 'Reputation' },
        { to: `/admin/${communityId}/ai-insights`, icon: SparklesIcon, label: 'AI Insights' },
        { to: `/admin/${communityId}/ai-config`, icon: Cog6ToothIcon, label: 'AI Config' },
        { to: `/admin/${communityId}/bot-detection`, icon: ShieldCheckIcon, label: 'Bot Detection' },
        { to: `/admin/${communityId}/modules`, icon: PuzzlePieceIcon, label: 'Modules' },
        { to: `/admin/${communityId}/stream-overlays`, icon: WindowIcon, label: 'Stream Overlays' },
        { to: `/admin/${communityId}/domains`, icon: GlobeAltIcon, label: 'Custom Domains' },
        { to: `/admin/${communityId}/shoutouts`, icon: SpeakerWaveIcon, label: 'Shoutouts' },
        { to: `/admin/${communityId}/translation`, icon: LanguageIcon, label: 'Translation & Captions' },
        { to: `/admin/${communityId}/loyalty`, icon: CurrencyDollarIcon, label: 'Loyalty System' },
      ]
    : [];

  // Platform admin nav
  const platformAdminNav = [
    { to: '/platform', icon: ChartBarIcon, label: 'Dashboard', exact: true },
    { to: '/platform/users', icon: UserGroupIcon, label: 'Users' },
    { to: '/platform/communities', icon: HomeIcon, label: 'Communities' },
  ];

  // Super admin nav
  const superAdminNav = [
    { to: '/superadmin', icon: ChartBarIcon, label: 'Dashboard', exact: true },
    { to: '/superadmin/communities', icon: HomeIcon, label: 'Communities' },
    { to: '/superadmin/modules', icon: BuildingStorefrontIcon, label: 'Module Registry' },
    { to: '/superadmin/platform-config', icon: Cog6ToothIcon, label: 'Platform Config' },
  ];

  const isActive = (to, exact = false) => {
    if (exact) return location.pathname === to;
    return location.pathname.startsWith(to);
  };

  // Determine which nav to show based on the path
  const isSuperAdminPath = location.pathname.startsWith('/superadmin');
  const navItems = communityId
    ? communityAdminNav
    : isSuperAdminPath
      ? superAdminNav
      : platformAdminNav;
  const title = communityId
    ? 'Community Admin'
    : isSuperAdminPath
      ? 'Super Admin'
      : 'Platform Admin';

  return (
    <div className="min-h-screen bg-navy-950">
      {/* Top bar */}
      <header className="bg-navy-900 border-b border-navy-700 sticky top-0 z-50">
        <div className="flex justify-between items-center h-16 px-4 sm:px-6 lg:px-8">
          <div className="flex items-center space-x-4">
            <Link to="/" className="flex items-center space-x-2">
              <img src="/waddlebot-logo.png" alt="Waddles" className="w-8 h-8" />
              <span className="text-xl font-bold text-gold-400">Waddles</span>
            </Link>
            <span className="text-navy-600">|</span>
            <div className="flex items-center space-x-2">
              <ShieldCheckIcon className="w-5 h-5 text-gold-400" />
              <span className="font-medium text-gold-400">{title}</span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {isSuperAdmin && (
              <Link
                to="/superadmin"
                className="text-sm font-medium text-gold-400 hover:text-gold-300"
              >
                Super Admin
              </Link>
            )}
            <Link to="/dashboard" className="text-sm text-navy-300 hover:text-sky-300">
              Back to Dashboard
            </Link>
            <div className="flex items-center space-x-2">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt={user.username} className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-navy-700 flex items-center justify-center border border-navy-600">
                  <span className="text-sky-100 font-medium">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <span className="text-sm text-sky-100">{user?.username}</span>
            </div>
            <button
              onClick={logout}
              className="p-2 text-navy-400 hover:text-sky-300 rounded-lg hover:bg-navy-800"
            >
              <ArrowLeftOnRectangleIcon className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-navy-900 border-r border-navy-700 min-h-[calc(100vh-4rem)] sticky top-16">
          <nav className="p-4 space-y-1">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center justify-between px-3 py-2 rounded-lg transition-colors ${
                  isActive(item.to, item.exact)
                    ? 'bg-gold-500/20 text-gold-400 border border-gold-500/30'
                    : 'text-navy-300 hover:bg-navy-800 hover:text-sky-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <item.icon className="w-5 h-5" />
                  <span className="text-sm font-medium">{item.label}</span>
                </div>
                {item.premium && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-gold-500 text-navy-900 font-bold">
                    PRO
                  </span>
                )}
              </Link>
            ))}

            {communityId && (
              <>
                <div className="pt-6 pb-2">
                  <div className="text-xs font-semibold text-navy-500 uppercase tracking-wider px-3">
                    Quick Actions
                  </div>
                </div>
                <Link
                  to={`/dashboard/community/${communityId}`}
                  className="flex items-center space-x-3 px-3 py-2 rounded-lg text-navy-300 hover:bg-navy-800 hover:text-sky-300"
                >
                  <DocumentTextIcon className="w-5 h-5" />
                  <span className="text-sm font-medium">View Community</span>
                </Link>
              </>
            )}

            {isPlatformAdmin && communityId && (
              <Link
                to="/platform"
                className="flex items-center space-x-3 px-3 py-2 rounded-lg text-navy-300 hover:bg-navy-800 hover:text-sky-300"
              >
                <ShieldCheckIcon className="w-5 h-5" />
                <span className="text-sm font-medium">Platform Admin</span>
              </Link>
            )}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default AdminLayout;
