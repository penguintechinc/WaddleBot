/**
 * Regression test for the OAuth callback page's URL contract.
 *
 * The page used to read `?token=...` off the URL and hand it straight to
 * `handleOAuthCallback` as if it were the session JWT. The backend hotfix
 * redirects with `?code=...` instead (an opaque, single-use exchange code --
 * see hub_api/blueprints/v1/auth.py::oauth_callback) -- this pins that the
 * page reads `code`, not `token`, and never treats a `token` param as
 * meaningful.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import OAuthCallback from '../OAuthCallback';
import * as AuthContext from '../../../contexts/AuthContext';

const handleOAuthCallback = vi.fn();
const navigateSpy = vi.fn();

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => navigateSpy,
  };
});

function mount(path) {
  vi.spyOn(AuthContext, 'useAuth').mockReturnValue({ handleOAuthCallback });
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/auth/callback" element={<OAuthCallback />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('OAuthCallback', () => {
  it('exchanges the code query param, never a token param', async () => {
    handleOAuthCallback.mockResolvedValue(undefined);
    mount('/auth/callback?code=the-exchange-code');

    await waitFor(() => expect(handleOAuthCallback).toHaveBeenCalledWith('the-exchange-code'));
    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith('/dashboard'));
  });

  it('ignores a token query param entirely -- it is never a valid handoff shape anymore', async () => {
    mount('/auth/callback?token=leaked-jwt-value');

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith('/login?error=missing_code'));
    expect(handleOAuthCallback).not.toHaveBeenCalled();
  });

  it('redirects to login with the provider error when present', async () => {
    mount('/auth/callback?error=oauth_denied');

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith('/login?error=oauth_denied'));
    expect(handleOAuthCallback).not.toHaveBeenCalled();
  });

  it('sends the user back to login if the exchange itself fails', async () => {
    handleOAuthCallback.mockRejectedValue(new Error('invalid or expired exchange code'));
    mount('/auth/callback?code=the-exchange-code');

    await waitFor(() => expect(navigateSpy).toHaveBeenCalledWith('/login?error=oauth_failed'));
  });
});
