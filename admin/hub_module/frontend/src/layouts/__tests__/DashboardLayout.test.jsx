import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Capture props passed to SidebarMenu for assertion
let capturedProps = {};
vi.mock('@penguintechinc/react-libs', () => ({
  SidebarMenu: (props) => {
    capturedProps = props;
    return null;
  },
}));
vi.mock('../../components/GlobalBanner', () => ({ default: () => null }));
vi.mock('../../components/VendorRequestFooter', () => ({ default: () => null }));

const mockAuth = {
  user: { username: 'testuser', displayName: 'Test User' },
  logout: vi.fn(),
  isSuperAdmin: false,
  isVendor: false,
  isAnalyticsConsumer: false,
  isCommunityAdmin: vi.fn(() => false),
};

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockAuth,
}));

const { default: DashboardLayout } = await import('../DashboardLayout');

// Render under the route pattern that best matches the path so useParams extracts :id correctly
const routePatternFor = (path) => {
  if (path.startsWith('/dashboard/community/')) return '/dashboard/community/:id/*';
  if (path.startsWith('/admin/')) return '/admin/:id/*';
  if (path.startsWith('/superadmin')) return '/superadmin/*';
  return '/dashboard/*';
};

const renderAt = (path) => {
  capturedProps = {};
  const pattern = routePatternFor(path);
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={pattern} element={<DashboardLayout />} />
      </Routes>
    </MemoryRouter>
  );
  return capturedProps;
};

describe('DashboardLayout — activeGroupKey', () => {
  beforeEach(() => {
    mockAuth.isCommunityAdmin.mockReturnValue(false);
    mockAuth.isSuperAdmin = false;
    mockAuth.isVendor = false;
    mockAuth.isAnalyticsConsumer = false;
  });

  it('is "main" on /dashboard', () => {
    const props = renderAt('/dashboard');
    expect(props.activeGroupKey).toBe('main');
  });

  it('is "community" on /dashboard/community/:id', () => {
    const props = renderAt('/dashboard/community/abc');
    expect(props.activeGroupKey).toBe('community');
  });

  it('is "community-admin" on /admin/:id', () => {
    const props = renderAt('/admin/abc');
    expect(props.activeGroupKey).toBe('community-admin');
  });

  it('is "super-admin" on /superadmin', () => {
    const props = renderAt('/superadmin');
    expect(props.activeGroupKey).toBe('super-admin');
  });
});

describe('DashboardLayout — categories construction', () => {
  beforeEach(() => {
    mockAuth.isCommunityAdmin.mockReturnValue(false);
    mockAuth.isSuperAdmin = false;
    mockAuth.isVendor = false;
    mockAuth.isAnalyticsConsumer = false;
  });

  it('produces "main" category when no communityId', () => {
    const props = renderAt('/dashboard');
    expect(props.categories.find((c) => c.key === 'main')).toBeTruthy();
  });

  it('"main" category is not collapsible', () => {
    const props = renderAt('/dashboard');
    const main = props.categories.find((c) => c.key === 'main');
    expect(main.collapsible).toBe(false);
  });

  it('produces "community" category when communityId present', () => {
    const props = renderAt('/dashboard/community/abc');
    expect(props.categories.find((c) => c.key === 'community')).toBeTruthy();
  });

  it('does not include "community-admin" when isCommunityAdmin returns false', () => {
    const props = renderAt('/dashboard/community/abc');
    expect(props.categories.find((c) => c.key === 'community-admin')).toBeFalsy();
  });

  it('includes "community-admin" when isCommunityAdmin returns true', () => {
    mockAuth.isCommunityAdmin.mockReturnValue(true);
    const props = renderAt('/dashboard/community/abc');
    expect(props.categories.find((c) => c.key === 'community-admin')).toBeTruthy();
  });

  it('does not include vendor when isVendor is false', () => {
    const props = renderAt('/dashboard');
    expect(props.categories.find((c) => c.key === 'vendor')).toBeFalsy();
  });

  it('does not include super-admin when isSuperAdmin is false', () => {
    const props = renderAt('/dashboard');
    expect(props.categories.find((c) => c.key === 'super-admin')).toBeFalsy();
  });

  it('includes super-admin when isSuperAdmin is true', () => {
    mockAuth.isSuperAdmin = true;
    const props = renderAt('/superadmin');
    expect(props.categories.find((c) => c.key === 'super-admin')).toBeTruthy();
  });

  it('includes vendor when isVendor is true', () => {
    mockAuth.isVendor = true;
    const props = renderAt('/dashboard');
    expect(props.categories.find((c) => c.key === 'vendor')).toBeTruthy();
  });

  it('passes autoCollapse=true to SidebarMenu', () => {
    const props = renderAt('/dashboard');
    expect(props.autoCollapse).toBe(true);
  });

  it('passes activeGroupKey to SidebarMenu', () => {
    const props = renderAt('/dashboard');
    expect(props.activeGroupKey).toBeDefined();
  });

  it('onNavigate prop is callable without throwing', () => {
    const props = renderAt('/dashboard');
    expect(() => props.onNavigate('/dashboard')).not.toThrow();
  });
});
