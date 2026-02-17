import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';

// Layouts
import PublicLayout from './layouts/PublicLayout';
import DashboardLayout from './layouts/DashboardLayout';
import AdminLayout from './layouts/AdminLayout';

// Public pages
import HomePage from './pages/public/HomePage';
import CommunitiesPage from './pages/public/CommunitiesPage';
import CommunityPublicPage from './pages/public/CommunityPublicPage';
import LiveStreamsPage from './pages/public/LiveStreamsPage';
import UserPublicProfile from './pages/public/UserPublicProfile';

// Auth pages
import LoginPage from './pages/auth/LoginPage';
import OAuthCallback from './pages/auth/OAuthCallback';

// Cookie Policy page
import CookiePolicy from './pages/CookiePolicy';

// Calendar pages
import CalendarSettings from './pages/calendar/CalendarSettings';
import BookingPages from './pages/calendar/BookingPages';
import MyBookings from './pages/calendar/MyBookings';
import BookingPagePublic from './pages/calendar/BookingPagePublic';

// Dashboard pages
import DashboardHome from './pages/dashboard/DashboardHome';
import CommunityDashboard from './pages/dashboard/CommunityDashboard';
import CommunitySettings from './pages/dashboard/CommunitySettings';
import CommunityChat from './pages/dashboard/CommunityChat';
import CommunityLeaderboard from './pages/dashboard/CommunityLeaderboard';
import CommunityMembers from './pages/dashboard/CommunityMembers';
import AccountSettings from './pages/dashboard/AccountSettings';
import UserProfileEdit from './pages/dashboard/UserProfileEdit';
import CreateCommunity from './pages/dashboard/CreateCommunity';

// Admin pages
import AdminHome from './pages/admin/AdminHome';
import AdminMembers from './pages/admin/AdminMembers';
import AdminModules from './pages/admin/AdminModules';
import AdminMarketplace from './pages/admin/AdminMarketplace';
import AdminStreamOverlays from './pages/admin/AdminStreamOverlays';
import AdminDomains from './pages/admin/AdminDomains';
import AdminServers from './pages/admin/AdminServers';
import AdminConnectedPlatforms from './pages/admin/AdminConnectedPlatforms';
import AdminMirrorGroups from './pages/admin/AdminMirrorGroups';
import AdminLeaderboardConfig from './pages/admin/AdminLeaderboardConfig';
import AdminCommunityProfile from './pages/admin/AdminCommunityProfile';
import ReputationSettings from './pages/admin/ReputationSettings';
import AdminAIInsights from './pages/admin/AdminAIInsights';
import AdminAIResearcherConfig from './pages/admin/AdminAIResearcherConfig';
import AdminBotDetection from './pages/admin/AdminBotDetection';
import AdminAnnouncements from './pages/admin/AdminAnnouncements';
import AdminAnalytics from './pages/admin/AdminAnalytics';
import AdminSecurity from './pages/admin/AdminSecurity';
import LoyaltySettings from './pages/admin/LoyaltySettings';
import LoyaltyLeaderboard from './pages/admin/LoyaltyLeaderboard';
import LoyaltyGiveaways from './pages/admin/LoyaltyGiveaways';
import LoyaltyGames from './pages/admin/LoyaltyGames';
import LoyaltyGear from './pages/admin/LoyaltyGear';
import AdminWorkflows from './pages/admin/AdminWorkflows';
import AdminShoutouts from './pages/admin/AdminShoutouts';
import AdminTranslation from './pages/admin/AdminTranslation';
import AdminMusicDashboard from './pages/admin/AdminMusicDashboard';
import AdminMusicSettings from './pages/admin/AdminMusicSettings';
import AdminMusicProviders from './pages/admin/AdminMusicProviders';
import AdminRadioStations from './pages/admin/AdminRadioStations';
import AdminVendorReview from './pages/admin/AdminVendorReview';
import AdminCalendarTicketing from './pages/admin/AdminCalendarTicketing';
import AdminCalendarScanner from './pages/admin/AdminCalendarScanner';
import AdminCalendarAttendance from './pages/admin/AdminCalendarAttendance';
import AdminLiveStreams from './pages/admin/AdminLiveStreams';
import AdminCommunityCalls from './pages/admin/AdminCommunityCalls';
import AdminPolls from './pages/admin/AdminPolls';
import AdminForms from './pages/admin/AdminForms';

// Vendor pages
import VendorSubmissionForm from './pages/vendor/VendorSubmissionForm';
import VendorSubmissionStatus from './pages/vendor/VendorSubmissionStatus';
import VendorDashboard from './pages/vendor/VendorDashboard';
import VendorSubmissions from './pages/vendor/VendorSubmissions';
import VendorRequest from './pages/vendor/VendorRequest';

// Platform admin pages
import PlatformDashboard from './pages/platform/PlatformDashboard';
import PlatformUsers from './pages/platform/PlatformUsers';
import PlatformCommunities from './pages/platform/PlatformCommunities';

// Super admin pages
import SuperAdminDashboard from './pages/superadmin/SuperAdminDashboard';
import SuperAdminCommunities from './pages/superadmin/SuperAdminCommunities';
import SuperAdminCreateCommunity from './pages/superadmin/SuperAdminCreateCommunity';
import SuperAdminModuleRegistry from './pages/superadmin/SuperAdminModuleRegistry';
import SuperAdminPlatformConfig from './pages/superadmin/SuperAdminPlatformConfig';
import SuperAdminKongGateway from './pages/superadmin/SuperAdminKongGateway';
import SuperAdminSoftwareDiscovery from './pages/superadmin/SuperAdminSoftwareDiscovery';
import SuperAdminServiceDiscovery from './pages/superadmin/SuperAdminServiceDiscovery';
import SuperAdminVendorRequests from './pages/superadmin/SuperAdminVendorRequests';
import SuperAdminUsers from './pages/superadmin/SuperAdminUsers';

// Loading spinner
function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
    </div>
  );
}

// Protected route wrapper
function ProtectedRoute({ children, requireAdmin = false, requirePlatformAdmin = false, requireSuperAdmin = false }) {
  const { user, loading, hasRole } = useAuth();

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !hasRole('admin') && !hasRole('super_admin')) {
    return <Navigate to="/dashboard" replace />;
  }

  if (requirePlatformAdmin && !hasRole('platform-admin')) {
    return <Navigate to="/dashboard" replace />;
  }

  if (requireSuperAdmin && !hasRole('super_admin')) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

function App() {
  return (
    <Routes>
      {/* Public routes */}
      <Route element={<PublicLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/communities" element={<CommunitiesPage />} />
        <Route path="/communities/:id" element={<CommunityPublicPage />} />
        <Route path="/live" element={<LiveStreamsPage />} />
        <Route path="/users/:userId" element={<UserPublicProfile />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/auth/callback" element={<OAuthCallback />} />
        <Route path="/cookie-policy" element={<CookiePolicy />} />

        {/* Public booking page (no auth required) */}
        <Route path="/book/:slug" element={<BookingPagePublic />} />

        {/* Vendor submission routes (public) */}
        <Route path="/vendor/submit" element={<VendorSubmissionForm />} />
        <Route path="/vendor/submission-status" element={<VendorSubmissionStatus />} />
      </Route>

      {/* Dashboard routes (authenticated) */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardHome />} />
        <Route path="/dashboard/settings" element={<AccountSettings />} />
        <Route path="/dashboard/profile" element={<UserProfileEdit />} />
        <Route path="/communities/create" element={<CreateCommunity />} />
        <Route path="/dashboard/community/:id" element={<CommunityDashboard />} />
        <Route path="/dashboard/community/:id/settings" element={<CommunitySettings />} />
        <Route path="/dashboard/community/:id/chat" element={<CommunityChat />} />
        <Route path="/dashboard/community/:id/leaderboard" element={<CommunityLeaderboard />} />
        <Route path="/dashboard/community/:id/members" element={<CommunityMembers />} />

        {/* Calendar routes (authenticated) */}
        <Route path="/calendar/settings" element={<CalendarSettings />} />
        <Route path="/calendar/booking-pages" element={<BookingPages />} />
        <Route path="/calendar/my-bookings" element={<MyBookings />} />

        {/* Vendor dashboard routes (authenticated vendors) */}
        <Route path="/vendor/dashboard" element={<VendorDashboard />} />
        <Route path="/vendor/submissions" element={<VendorSubmissions />} />
        <Route path="/vendor/request" element={<VendorRequest />} />
      </Route>

      {/* Admin routes (community admin) */}
      <Route
        element={
          <ProtectedRoute requireAdmin>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/admin/:communityId" element={<AdminHome />} />
        <Route path="/admin/:communityId/members" element={<AdminMembers />} />
        <Route path="/admin/:communityId/workflows" element={<AdminWorkflows />} />
        <Route path="/admin/:communityId/modules" element={<AdminModules />} />
        <Route path="/admin/:communityId/marketplace" element={<AdminMarketplace />} />
        <Route path="/admin/:communityId/stream-overlays" element={<AdminStreamOverlays />} />
        <Route path="/admin/:communityId/domains" element={<AdminDomains />} />
        <Route path="/admin/:communityId/servers" element={<AdminServers />} />
        <Route path="/admin/:communityId/connected-platforms" element={<AdminConnectedPlatforms />} />
        <Route path="/admin/:communityId/mirror-groups" element={<AdminMirrorGroups />} />
        <Route path="/admin/:communityId/leaderboard" element={<AdminLeaderboardConfig />} />
        <Route path="/admin/:communityId/profile" element={<AdminCommunityProfile />} />
        <Route path="/admin/:communityId/reputation" element={<ReputationSettings />} />
        <Route path="/admin/:communityId/ai-insights" element={<AdminAIInsights />} />
        <Route path="/admin/:communityId/ai-config" element={<AdminAIResearcherConfig />} />
        <Route path="/admin/:communityId/bot-detection" element={<AdminBotDetection />} />
        <Route path="/admin/:communityId/announcements" element={<AdminAnnouncements />} />
        <Route path="/admin/:communityId/analytics" element={<AdminAnalytics />} />
        <Route path="/admin/:communityId/security" element={<AdminSecurity />} />
        <Route path="/admin/:communityId/loyalty" element={<LoyaltySettings />} />
        <Route path="/admin/:communityId/loyalty/leaderboard" element={<LoyaltyLeaderboard />} />
        <Route path="/admin/:communityId/loyalty/giveaways" element={<LoyaltyGiveaways />} />
        <Route path="/admin/:communityId/loyalty/games" element={<LoyaltyGames />} />
        <Route path="/admin/:communityId/loyalty/gear" element={<LoyaltyGear />} />
        <Route path="/admin/:communityId/shoutouts" element={<AdminShoutouts />} />
        <Route path="/admin/:communityId/translation" element={<AdminTranslation />} />
        <Route path="/admin/:communityId/music" element={<AdminMusicDashboard />} />
        <Route path="/admin/:communityId/music/settings" element={<AdminMusicSettings />} />
        <Route path="/admin/:communityId/music/providers" element={<AdminMusicProviders />} />
        <Route path="/admin/:communityId/music/radio" element={<AdminRadioStations />} />
        <Route path="/admin/:communityId/calendar/events/:eventId/tickets" element={<AdminCalendarTicketing />} />
        <Route path="/admin/:communityId/calendar/events/:eventId/scanner" element={<AdminCalendarScanner />} />
        <Route path="/admin/:communityId/calendar/events/:eventId/attendance" element={<AdminCalendarAttendance />} />
        <Route path="/admin/:communityId/live-streaming" element={<AdminLiveStreams />} />
        <Route path="/admin/:communityId/calls" element={<AdminCommunityCalls />} />
        <Route path="/admin/:communityId/polls" element={<AdminPolls />} />
        <Route path="/admin/:communityId/forms" element={<AdminForms />} />
      </Route>

      {/* Platform admin routes */}
      <Route
        element={
          <ProtectedRoute requirePlatformAdmin>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/platform" element={<PlatformDashboard />} />
        <Route path="/platform/users" element={<PlatformUsers />} />
        <Route path="/platform/communities" element={<PlatformCommunities />} />
      </Route>

      {/* Super admin routes - uses DashboardLayout with sidebar admin section */}
      <Route
        element={
          <ProtectedRoute requireSuperAdmin>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/superadmin" element={<SuperAdminDashboard />} />
        <Route path="/superadmin/communities" element={<SuperAdminCommunities />} />
        <Route path="/superadmin/communities/new" element={<SuperAdminCreateCommunity />} />
        <Route path="/superadmin/modules" element={<SuperAdminModuleRegistry />} />
        <Route path="/superadmin/vendor-submissions" element={<AdminVendorReview />} />
        <Route path="/superadmin/vendor-submissions/:submissionId" element={<AdminVendorReview />} />
        <Route path="/superadmin/vendor-requests" element={<SuperAdminVendorRequests />} />
        <Route path="/superadmin/users" element={<SuperAdminUsers />} />
        <Route path="/superadmin/platform-config" element={<SuperAdminPlatformConfig />} />
        <Route path="/superadmin/kong" element={<SuperAdminKongGateway />} />
        <Route path="/superadmin/software-discovery" element={<SuperAdminSoftwareDiscovery />} />
        <Route path="/superadmin/services" element={<SuperAdminServiceDiscovery />} />
      </Route>

      {/* Catch all - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
