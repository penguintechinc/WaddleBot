import { Outlet, Link, useLocation, useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import VendorRequestFooter from '../components/VendorRequestFooter';
import {
  HomeIcon,
  UserGroupIcon,
  CalendarIcon,
  ChatBubbleLeftRightIcon,
  Cog6ToothIcon,
  ArrowLeftOnRectangleIcon,
  UserCircleIcon,
  UserIcon,
  ChartBarIcon,
  BuildingStorefrontIcon,
  ShieldCheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ShoppingCartIcon,
  LinkIcon,
  TrophyIcon,
  InboxStackIcon,
  ServerStackIcon,
  TicketIcon,
} from '@heroicons/react/24/outline';
import { useState } from 'react';
import GlobalBanner from '../components/GlobalBanner';

function DashboardLayout() {
  const { user, logout, isSuperAdmin, isVendor } = useAuth();
  const location = useLocation();
  const { id: communityId } = useParams();
  const [adminCollapsed, setAdminCollapsed] = useState(false);
  const [vendorCollapsed, setVendorCollapsed] = useState(false);

  const mainNav = [
    { to: '/dashboard', icon: HomeIcon, label: 'My Communities' },
    { to: '/dashboard/profile', icon: UserIcon, label: 'My Profile' },
    { to: '/dashboard/settings', icon: UserCircleIcon, label: 'Account Settings' },
    { to: '/dashboard/my-channels', icon: LinkIcon, label: 'My Channels' },
  ];

  // Super Admin navigation
  const superAdminNav = [
    { to: '/superadmin', icon: ChartBarIcon, label: 'Dashboard', exact: true },
    { to: '/superadmin/communities', icon: HomeIcon, label: 'Communities' },
    { to: '/superadmin/modules', icon: BuildingStorefrontIcon, label: 'Module Registry' },
    { to: '/superadmin/users', icon: UserIcon, label: 'User Management' },
    { to: '/superadmin/vendor-requests', icon: ShoppingCartIcon, label: 'Vendor Requests' },
    { to: '/superadmin/analytics', icon: ChartBarIcon, label: 'Analytics' },
    { to: '/superadmin/platform-config', icon: Cog6ToothIcon, label: 'Platform Config' },
  ];

  // Vendor navigation (standalone - vendors are not admins)
  const vendorNav = [
    { to: '/vendor/dashboard', icon: ChartBarIcon, label: 'Dashboard', exact: true },
    { to: '/vendor/submissions', icon: BuildingStorefrontIcon, label: 'My Submissions' },
    { to: '/vendor/submit', icon: ShoppingCartIcon, label: 'Submit New Module' },
  ];

  const communityNav = communityId
    ? [
        { to: `/dashboard/community/${communityId}`, icon: HomeIcon, label: 'Overview', exact: true },
        { to: `/dashboard/community/${communityId}/members`, icon: UserGroupIcon, label: 'Members' },
        { to: `/community/${communityId}/interact`, icon: ChatBubbleLeftRightIcon, label: 'Chat & Forums' },
        { to: `/dashboard/community/${communityId}/leaderboard`, icon: TrophyIcon, label: 'Leaderboard' },
        { to: `/community/${communityId}/inventory`, icon: InboxStackIcon, label: 'Inventory' },
        { to: `/community/${communityId}/game-servers`, icon: ServerStackIcon, label: 'Game Servers' },
        { to: `/community/${communityId}/support/submit`, icon: TicketIcon, label: 'Support' },
        { to: `/dashboard/community/${communityId}/settings`, icon: Cog6ToothIcon, label: 'Settings' },
      ]
    : [];

  return (
    <div className="min-h-screen bg-navy-950">
      <GlobalBanner />
      {/* Top bar */}
      <header className="bg-navy-900 border-b border-navy-700 sticky top-0 z-50">
        <div className="flex justify-between items-center h-16 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center space-x-2">
            <img src="/waddlebot-logo.png" alt="Waddles" className="w-8 h-8" />
            <span className="text-xl font-bold text-gold-400">Waddles</span>
          </Link>

          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt={user.username} className="w-8 h-8 rounded-full" />
              ) : (
                <div className="w-8 h-8 rounded-full bg-navy-700 flex items-center justify-center border border-navy-600">
                  <span className="text-sky-400 font-medium">
                    {user?.username?.charAt(0).toUpperCase()}
                  </span>
                </div>
              )}
              <span className="text-sm font-medium text-sky-100">{user?.username}</span>
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
            {mainNav.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                  location.pathname === item.to
                    ? 'bg-navy-800 text-gold-400'
                    : 'text-navy-300 hover:bg-navy-800 hover:text-sky-300'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            ))}

            {communityNav.length > 0 && (
              <>
                <div className="pt-4 pb-2">
                  <div className="text-xs font-semibold text-navy-500 uppercase tracking-wider px-3">
                    Community
                  </div>
                </div>
                {communityNav.map((item) => {
                  const isActive = item.exact
                    ? location.pathname === item.to
                    : location.pathname.startsWith(item.to);
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-navy-800 text-gold-400'
                          : 'text-navy-300 hover:bg-navy-800 hover:text-sky-300'
                      }`}
                    >
                      <item.icon className="w-5 h-5" />
                      <span className="text-sm font-medium">{item.label}</span>
                    </Link>
                  );
                })}

                {/* Admin link */}
                <Link
                  to={`/admin/${communityId}`}
                  className="flex items-center space-x-3 px-3 py-2 rounded-lg text-gold-400 hover:bg-navy-800"
                >
                  <Cog6ToothIcon className="w-5 h-5" />
                  <span className="text-sm font-medium">Admin Panel</span>
                </Link>
              </>
            )}

            {/* Vendor Section - Standalone for vendors (appears first) */}
            {isVendor && (
              <div className="mt-6">
                <button
                  onClick={() => setVendorCollapsed(!vendorCollapsed)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-navy-500 uppercase tracking-wider hover:text-navy-400 transition-colors"
                >
                  <span className="flex items-center space-x-2">
                    <ShoppingCartIcon className="w-4 h-4" />
                    <span>Vendor</span>
                  </span>
                  {vendorCollapsed ? (
                    <ChevronRightIcon className="w-4 h-4" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4" />
                  )}
                </button>
                {!vendorCollapsed && (
                  <div className="mt-1 space-y-1">
                    {vendorNav.map((item) => {
                      const isActive = item.exact
                        ? location.pathname === item.to
                        : location.pathname.startsWith(item.to);
                      return (
                        <Link
                          key={item.to}
                          to={item.to}
                          className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                            isActive
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                              : 'text-navy-300 hover:bg-navy-800 hover:text-emerald-300'
                          }`}
                        >
                          <item.icon className="w-5 h-5" />
                          <span className="text-sm font-medium">{item.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* Super Admin Section - Role-based (appears second) */}
            {isSuperAdmin && (
              <div className="mt-6">
                <button
                  onClick={() => setAdminCollapsed(!adminCollapsed)}
                  className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-navy-500 uppercase tracking-wider hover:text-navy-400 transition-colors"
                >
                  <span className="flex items-center space-x-2">
                    <ShieldCheckIcon className="w-4 h-4" />
                    <span>Super Admin</span>
                  </span>
                  {adminCollapsed ? (
                    <ChevronRightIcon className="w-4 h-4" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4" />
                  )}
                </button>
                {!adminCollapsed && (
                  <div className="mt-1 space-y-1">
                    {superAdminNav.map((item) => {
                      const isActive = item.exact
                        ? location.pathname === item.to
                        : location.pathname.startsWith(item.to);
                      return (
                        <Link
                          key={item.to}
                          to={item.to}
                          className={`flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                            isActive
                              ? 'bg-gold-500/20 text-gold-400 border border-gold-500/30'
                              : 'text-navy-300 hover:bg-navy-800 hover:text-gold-300'
                          }`}
                        >
                          <item.icon className="w-5 h-5" />
                          <span className="text-sm font-medium">{item.label}</span>
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6">
          <Outlet />
        </main>
      </div>
      <VendorRequestFooter />
    </div>
  );
}

export default DashboardLayout;
