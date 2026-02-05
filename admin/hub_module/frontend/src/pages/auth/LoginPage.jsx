import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import axios from 'axios';

function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login, loginWithOAuth, register, error: authError, isAuthenticated } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [localError, setLocalError] = useState('');
  const [signupSettings, setSignupSettings] = useState({ signupEnabled: false, loading: true });
  const [verificationSent, setVerificationSent] = useState(false);
  const [resendingVerification, setResendingVerification] = useState(false);

  // Fetch signup settings on mount
  useEffect(() => {
    const fetchSignupSettings = async () => {
      try {
        const response = await axios.get('/api/v1/signup-settings');
        setSignupSettings({
          signupEnabled: response.data.signupEnabled,
          allowedDomains: response.data.allowedDomains,
          loading: false
        });
      } catch {
        setSignupSettings({ signupEnabled: false, loading: false });
      }
    };
    fetchSignupSettings();
  }, []);

  // Check for OAuth errors in URL
  useEffect(() => {
    const error = searchParams.get('error');
    if (error === 'oauth_denied') {
      setLocalError('OAuth authorization was denied');
    } else if (error === 'oauth_failed') {
      setLocalError('OAuth login failed. Please try again.');
    } else if (error === 'invalid_state') {
      setLocalError('Invalid OAuth state. Please try again.');
    }
  }, [searchParams]);

  // Redirect if already logged in
  if (isAuthenticated) {
    navigate('/dashboard');
    return null;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalError('');
    setLoading(true);

    try {
      if (mode === 'register') {
        const result = await register(email, password, username);
        // Check if email verification is required
        if (result?.requiresVerification) {
          setVerificationSent(true);
          return;
        }
      } else {
        const result = await login(email, password);
        // Check if user needs to verify email
        if (result?.requiresVerification) {
          setLocalError('Please verify your email address before logging in');
          setVerificationSent(true);
          return;
        }
      }
      navigate('/dashboard');
    } catch (err) {
      // Handle verification required from login
      if (err.requiresVerification) {
        setLocalError('Please verify your email address before logging in');
        setVerificationSent(true);
      } else {
        setLocalError(err.message || 'Authentication failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendingVerification(true);
    try {
      await axios.post('/api/v1/auth/resend-verification', { email });
      setLocalError('');
      alert('Verification email sent! Please check your inbox.');
    } catch (err) {
      setLocalError(err.response?.data?.message || 'Failed to resend verification email');
    } finally {
      setResendingVerification(false);
    }
  };

  const handleOAuth = async (platform) => {
    setLocalError('');
    setLoading(true);
    try {
      await loginWithOAuth(platform);
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <img src="/waddlebot-logo.png" alt="Waddles" className="w-24 h-24" />
          </div>
          <h1 className="text-3xl font-bold mt-4 gradient-text">Welcome to Waddles</h1>
          <p className="text-navy-300 mt-2">
            {mode === 'register' ? 'Create your account' : 'Sign in to access your communities'}
          </p>
        </div>

        <div className="card p-6">
          {(authError || localError) && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg text-red-300 text-sm">
              {authError || localError}
            </div>
          )}

          {/* Verification Sent Message */}
          {verificationSent && (
            <div className="mb-4 p-4 bg-green-500/20 border border-green-500/30 rounded-lg">
              <h3 className="font-medium text-green-300 mb-2">Check your email!</h3>
              <p className="text-green-200/80 text-sm mb-3">
                {mode === 'register'
                  ? 'We\'ve sent a verification link to your email. Please verify your email to complete registration.'
                  : 'Your email hasn\'t been verified yet. Please check your inbox for the verification link.'}
              </p>
              <button
                onClick={handleResendVerification}
                disabled={resendingVerification || !email}
                className="text-sm text-green-300 hover:text-green-200 underline disabled:opacity-50"
              >
                {resendingVerification ? 'Sending...' : 'Resend verification email'}
              </button>
            </div>
          )}

          {/* OAuth Buttons */}
          <div className="space-y-3 mb-6">
            <button
              onClick={() => handleOAuth('discord')}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 px-4 py-3 bg-navy-800 border border-navy-600 rounded-lg hover:bg-navy-700 hover:border-[#5865F2] transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#5865F2">
                <path d="M20.317 4.3698a19.7913 19.7913 0 00-4.8851-1.5152.0741.0741 0 00-.0785.0371c-.211.3753-.4447.8648-.6083 1.2495-1.8447-.2762-3.68-.2762-5.4868 0-.1636-.3933-.4058-.8742-.6177-1.2495a.077.077 0 00-.0785-.037 19.7363 19.7363 0 00-4.8852 1.515.0699.0699 0 00-.0321.0277C.5334 9.0458-.319 13.5799.0992 18.0578a.0824.0824 0 00.0312.0561c2.0528 1.5076 4.0413 2.4228 5.9929 3.0294a.0777.0777 0 00.0842-.0276c.4616-.6304.8731-1.2952 1.226-1.9942a.076.076 0 00-.0416-.1057c-.6528-.2476-1.2743-.5495-1.8722-.8923a.077.077 0 01-.0076-.1277c.1258-.0943.2517-.1923.3718-.2914a.0743.0743 0 01.0776-.0105c3.9278 1.7933 8.18 1.7933 12.0614 0a.0739.0739 0 01.0785.0095c.1202.099.246.1981.3728.2924a.077.077 0 01-.0066.1276 12.2986 12.2986 0 01-1.873.8914.0766.0766 0 00-.0407.1067c.3604.698.7719 1.3628 1.225 1.9932a.076.076 0 00.0842.0286c1.961-.6067 3.9495-1.5219 6.0023-3.0294a.077.077 0 00.0313-.0552c.5004-5.177-.8382-9.6739-3.5485-13.6604a.061.061 0 00-.0312-.0286zM8.02 15.3312c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9555-2.4189 2.157-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.9555 2.4189-2.1569 2.4189zm7.9748 0c-1.1825 0-2.1569-1.0857-2.1569-2.419 0-1.3332.9554-2.4189 2.1569-2.4189 1.2108 0 2.1757 1.0952 2.1568 2.419 0 1.3332-.946 2.4189-2.1568 2.4189Z"/>
              </svg>
              <span className="font-medium text-sky-100">Continue with Discord</span>
            </button>

            <button
              onClick={() => handleOAuth('twitch')}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 px-4 py-3 bg-navy-800 border border-navy-600 rounded-lg hover:bg-navy-700 hover:border-[#9146FF] transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#9146FF">
                <path d="M11.571 4.714h1.715v5.143H11.57zm4.715 0H18v5.143h-1.714zM6 0L1.714 4.286v15.428h5.143V24l4.286-4.286h3.428L22.286 12V0zm14.571 11.143l-3.428 3.428h-3.429l-3 3v-3H6.857V1.714h13.714Z"/>
              </svg>
              <span className="font-medium text-sky-100">Continue with Twitch</span>
            </button>

            <button
              onClick={() => handleOAuth('slack')}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 px-4 py-3 bg-navy-800 border border-navy-600 rounded-lg hover:bg-navy-700 hover:border-[#36C5F0] transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#36C5F0">
                <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z"/>
              </svg>
              <span className="font-medium text-sky-100">Continue with Slack</span>
            </button>

            <button
              onClick={() => handleOAuth('youtube')}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 px-4 py-3 bg-navy-800 border border-navy-600 rounded-lg hover:bg-navy-700 hover:border-[#FF0000] transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#FF0000">
                <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
              </svg>
              <span className="font-medium text-sky-100">Continue with YouTube</span>
            </button>

            <button
              onClick={() => handleOAuth('kick')}
              disabled={loading}
              className="w-full flex items-center justify-center space-x-3 px-4 py-3 bg-navy-800 border border-navy-600 rounded-lg hover:bg-navy-700 hover:border-[#53FC18] transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="#53FC18">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"/>
              </svg>
              <span className="font-medium text-sky-100">Continue with KICK</span>
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-navy-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-navy-800 text-navy-400">or continue with email</span>
            </div>
          </div>

          {/* Email/Password Form */}
          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              {mode === 'register' && (
                <div>
                  <label className="block text-sm font-medium text-sky-200 mb-1">
                    Username
                  </label>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="input"
                    placeholder="Choose a username"
                    autoComplete="username"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-sky-200 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                  required
                  autoComplete="email"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-sky-200 mb-1">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder={mode === 'register' ? 'Choose a password (8+ characters)' : 'Enter your password'}
                  required
                  autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                  minLength={mode === 'register' ? 8 : undefined}
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full disabled:opacity-50"
              >
                {loading ? 'Please wait...' : mode === 'register' ? 'Create Account' : 'Sign In'}
              </button>
            </div>
          </form>

          {/* Toggle Login/Register - Only show signup if enabled */}
          <div className="mt-6 text-center">
            {mode === 'login' ? (
              signupSettings.signupEnabled && !signupSettings.loading ? (
                <p className="text-navy-400">
                  Don't have an account?{' '}
                  <button
                    onClick={() => { setMode('register'); setVerificationSent(false); }}
                    className="text-sky-400 hover:text-sky-300 font-medium"
                  >
                    Sign up
                  </button>
                  {signupSettings.allowedDomains && (
                    <span className="block text-xs text-navy-500 mt-1">
                      (Registration limited to: {signupSettings.allowedDomains.join(', ')})
                    </span>
                  )}
                </p>
              ) : null
            ) : (
              <p className="text-navy-400">
                Already have an account?{' '}
                <button
                  onClick={() => { setMode('login'); setVerificationSent(false); }}
                  className="text-sky-400 hover:text-sky-300 font-medium"
                >
                  Sign in
                </button>
              </p>
            )}
          </div>
        </div>

        {/* Footer note */}
        <p className="mt-6 text-center text-sm text-navy-500">
          By signing in, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
