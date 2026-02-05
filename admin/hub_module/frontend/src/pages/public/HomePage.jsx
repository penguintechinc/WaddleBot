import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { publicApi } from '../../services/api';

function HomePage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const response = await publicApi.getStats();
        setStats(response.data.stats);
      } catch (err) {
        console.error('Failed to fetch stats:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  return (
    <div>
      {/* Hero section */}
      <section className="bg-gradient-to-br from-navy-900 via-navy-800 to-navy-900 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl md:text-5xl font-bold mb-6 gradient-text">
            Unite Your Communities
          </h1>
          <p className="text-xl text-navy-300 max-w-2xl mx-auto mb-8">
            Waddles brings your Discord, Twitch, and Slack communities together with
            powerful tools for engagement, moderation, and growth.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Link to="/login" className="btn btn-primary px-8 py-3">
              Get Started
            </Link>
            <Link to="/communities" className="btn btn-outline px-8 py-3">
              Browse Communities
            </Link>
          </div>
        </div>
      </section>

      {/* Stats section */}
      <section className="py-16 bg-navy-900 border-t border-navy-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-bold text-gold-400">
                {loading ? '...' : stats?.communities || 0}
              </div>
              <div className="text-navy-400 mt-1">Communities</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-indigo-400">
                {loading ? '...' : stats?.discord?.servers || 0}
              </div>
              <div className="text-navy-400 mt-1">Discord Servers</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-purple-400">
                {loading ? '...' : stats?.twitch?.channels || 0}
              </div>
              <div className="text-navy-400 mt-1">Twitch Channels</div>
            </div>
            <div>
              <div className="text-4xl font-bold text-emerald-400">
                {loading ? '...' : stats?.slack?.workspaces || 0}
              </div>
              <div className="text-navy-400 mt-1">Slack Workspaces</div>
            </div>
          </div>
        </div>
      </section>

      {/* Features section */}
      <section className="py-20 bg-navy-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-12 text-sky-100">
            Everything You Need to Build Community
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="card p-6">
              <div className="text-3xl mb-4">🎮</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Multi-Platform</h3>
              <p className="text-navy-400">
                Connect Discord, Twitch, and Slack communities under one unified system.
              </p>
            </div>
            <div className="card p-6">
              <div className="text-3xl mb-4">🏆</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Reputation System</h3>
              <p className="text-navy-400">
                Track engagement and reward your most active community members.
              </p>
            </div>
            <div className="card p-6">
              <div className="text-3xl mb-4">🔧</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Modular Design</h3>
              <p className="text-navy-400">
                Add features with modules - from AI chat to music integration.
              </p>
            </div>
            <div className="card p-6">
              <div className="text-3xl mb-4">📺</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Browser Sources</h3>
              <p className="text-navy-400">
                Integrated OBS overlays for streams - tickers, alerts, and media.
              </p>
            </div>
            <div className="card p-6">
              <div className="text-3xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Analytics</h3>
              <p className="text-navy-400">
                Understand your community with detailed engagement metrics.
              </p>
            </div>
            <div className="card p-6">
              <div className="text-3xl mb-4">🔐</div>
              <h3 className="text-xl font-semibold mb-2 text-sky-100">Role Management</h3>
              <p className="text-navy-400">
                Flexible permissions with labels, roles, and identity linking.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA section */}
      <section className="py-20 bg-gradient-to-r from-navy-900 via-navy-800 to-navy-900 border-t border-navy-700">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold mb-4 text-sky-100">Ready to Grow Your Community?</h2>
          <p className="text-navy-400 mb-8">
            Join hundreds of communities already using Waddles to engage their audience.
          </p>
          <Link to="/login" className="btn btn-primary px-8 py-3">
            Start Free Today
          </Link>
        </div>
      </section>
    </div>
  );
}

export default HomePage;
