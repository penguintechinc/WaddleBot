import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import api from '../../services/api';
import { FormModalBuilder } from '@penguin/react_libs';

// Waddles theme colors matching the existing UI
const waddlebotColors = {
  modalBackground: 'bg-navy-800',
  headerBackground: 'bg-navy-800',
  footerBackground: 'bg-navy-850',
  overlayBackground: 'bg-black bg-opacity-50',
  titleText: 'text-sky-100',
  labelText: 'text-sky-100',
  descriptionText: 'text-navy-400',
  errorText: 'text-red-400',
  buttonText: 'text-white',
  fieldBackground: 'bg-navy-700',
  fieldBorder: 'border-navy-600',
  fieldText: 'text-sky-100',
  fieldPlaceholder: 'placeholder-navy-400',
  focusRing: 'focus:ring-gold-500',
  focusBorder: 'focus:border-gold-500',
  primaryButton: 'bg-sky-600',
  primaryButtonHover: 'hover:bg-sky-700',
  secondaryButton: 'bg-navy-700',
  secondaryButtonHover: 'hover:bg-navy-600',
  secondaryButtonBorder: 'border-navy-600',
  activeTab: 'text-gold-400',
  activeTabBorder: 'border-gold-500',
  inactiveTab: 'text-navy-400',
  inactiveTabHover: 'hover:text-navy-300 hover:border-navy-500',
  tabBorder: 'border-navy-700',
  errorTabText: 'text-red-400',
  errorTabBorder: 'border-red-500',
};

const PLATFORM_ICONS = {
  discord: '🎮',
  twitch: '📺',
  slack: '💬',
  youtube: '▶️',
};

const PLATFORM_COLORS = {
  discord: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  twitch: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  slack: 'bg-green-500/20 text-green-300 border-green-500/30',
  youtube: 'bg-red-500/20 text-red-300 border-red-500/30',
};

function LoyaltyLeaderboard() {
  const { communityId } = useParams();
  const [users, setUsers] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState(null);
  const [search, setSearch] = useState('');
  const [platform, setPlatform] = useState('');
  const [message, setMessage] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  // Modal states
  const [showAdjustModal, setShowAdjustModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [showWipeModal, setShowWipeModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, [communityId, page, search, platform]);

  async function fetchData() {
    setLoading(true);
    try {
      const [leaderboardRes, statsRes] = await Promise.all([
        api.get(`/api/v1/admin/${communityId}/loyalty/leaderboard`, {
          params: { page, limit: 25, search, platform }
        }),
        api.get(`/api/v1/admin/${communityId}/loyalty/stats`)
      ]);
      setUsers(leaderboardRes.data.users || []);
      setPagination(leaderboardRes.data.pagination);
      setStats(statsRes.data.stats || {});
    } catch (err) {
      console.error('Failed to fetch loyalty data:', err);
      setMessage({ type: 'error', text: 'Failed to load loyalty data' });
    } finally {
      setLoading(false);
    }
  }

  function openAdjustModal(user) {
    setSelectedUser(user);
    setShowAdjustModal(true);
  }

  function closeAdjustModal() {
    setShowAdjustModal(false);
    setSelectedUser(null);
  }

  async function handleAdjustBalance(data) {
    const amount = parseFloat(data.amount);
    if (!data.amount || isNaN(amount) || amount <= 0) {
      setMessage({ type: 'error', text: 'Please enter a valid amount' });
      throw new Error('Please enter a valid amount');
    }

    if (!data.reason?.trim()) {
      setMessage({ type: 'error', text: 'Please provide a reason for this adjustment' });
      throw new Error('Please provide a reason for this adjustment');
    }

    setActionLoading(true);
    try {
      await api.put(`/api/v1/admin/${communityId}/loyalty/user/${selectedUser.userId}/balance`, {
        action: data.action,
        amount: amount,
        reason: data.reason.trim()
      });
      setMessage({ type: 'success', text: `Balance ${data.action} successful` });
      closeAdjustModal();
      fetchData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error?.message || `Failed to ${data.action} balance`
      });
      throw err;
    } finally {
      setActionLoading(false);
    }
  }

  async function handleWipeAll() {
    setActionLoading(true);
    try {
      await api.post(`/api/v1/admin/${communityId}/loyalty/wipe`);
      setMessage({ type: 'success', text: 'All currency balances have been wiped' });
      setShowWipeModal(false);
      fetchData();
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to wipe balances'
      });
      throw err;
    } finally {
      setActionLoading(false);
    }
  }

  // Build fields for Adjust Balance Modal
  const adjustBalanceFields = useMemo(() => [
    {
      name: 'action',
      type: 'select',
      label: 'Action',
      required: true,
      defaultValue: 'add',
      options: [
        { value: 'add', label: 'Add - Increase balance' },
        { value: 'remove', label: 'Remove - Decrease balance' },
        { value: 'set', label: 'Set Exact - Set to specific amount' },
      ],
    },
    {
      name: 'amount',
      type: 'number',
      label: 'Amount',
      required: true,
      placeholder: 'Enter amount...',
      min: 0,
      step: 1,
    },
    {
      name: 'reason',
      type: 'textarea',
      label: 'Reason',
      required: true,
      placeholder: 'Why are you adjusting this balance?',
      rows: 3,
    },
  ], []);

  // Build fields for Wipe Confirmation Modal
  const wipeConfirmFields = useMemo(() => [
    {
      name: 'confirmation',
      type: 'text',
      label: 'Type "WIPE ALL" to confirm',
      required: true,
      placeholder: 'WIPE ALL',
      helpText: `This will reset ALL user loyalty currency balances to zero. ${stats?.usersWithBalance || 0} users will lose a total of ${formatCurrency(stats?.totalCurrency || 0)} currency.`,
    },
  ], [stats]);

  function formatCurrency(amount) {
    return `💰 ${amount.toLocaleString()}`;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-sky-100">Loyalty Currency Leaderboard</h1>
        <button
          onClick={() => setShowWipeModal(true)}
          className="btn bg-red-500/20 text-red-300 border border-red-500/30 hover:bg-red-500/30"
        >
          Wipe All Currency
        </button>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-lg border ${
          message.type === 'success'
            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
            : 'bg-red-500/20 text-red-300 border-red-500/30'
        }`}>
          {message.text}
          <button onClick={() => setMessage(null)} className="float-right">×</button>
        </div>
      )}

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Total Currency in Circulation</div>
            <div className="text-2xl font-bold text-gold-400">
              {formatCurrency(stats.totalCurrency || 0)}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Users with Balances</div>
            <div className="text-2xl font-bold text-sky-400">
              {(stats.usersWithBalance || 0).toLocaleString()}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Average Balance</div>
            <div className="text-2xl font-bold text-purple-400">
              {formatCurrency(stats.averageBalance || 0)}
            </div>
          </div>
        </div>
      )}

      {/* Search and Filter */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <input
          type="search"
          placeholder="Search by username..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="input flex-1"
        />
        <select
          value={platform}
          onChange={(e) => { setPlatform(e.target.value); setPage(1); }}
          className="input w-full md:w-48"
        >
          <option value="">All Platforms</option>
          <option value="discord">Discord</option>
          <option value="twitch">Twitch</option>
          <option value="slack">Slack</option>
          <option value="youtube">YouTube</option>
        </select>
      </div>

      {/* Leaderboard Table */}
      <div className="card overflow-hidden">
        <table>
          <thead>
            <tr>
              <th className="w-16">Rank</th>
              <th>User</th>
              <th>Platform</th>
              <th className="text-right">Balance</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan="5" className="p-12 text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400 mx-auto"></div>
                </td>
              </tr>
            ) : users.length === 0 ? (
              <tr>
                <td colSpan="5" className="p-12 text-center text-navy-400">
                  No users found
                </td>
              </tr>
            ) : (
              users.map((user, index) => (
                <tr key={user.userId} className="hover:bg-navy-700/50 cursor-pointer">
                  <td className="text-center">
                    <div className={`font-bold ${
                      index === 0 ? 'text-gold-400 text-xl' :
                      index === 1 ? 'text-silver-400 text-lg' :
                      index === 2 ? 'text-bronze-400 text-lg' :
                      'text-navy-400'
                    }`}>
                      #{pagination ? ((page - 1) * 25) + index + 1 : index + 1}
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center space-x-3">
                      {user.avatarUrl ? (
                        <img src={user.avatarUrl} alt="" className="w-8 h-8 rounded-full" />
                      ) : (
                        <div className="w-8 h-8 rounded-full bg-navy-700 flex items-center justify-center text-sm">
                          {user.username?.[0]?.toUpperCase() || '?'}
                        </div>
                      )}
                      <div>
                        <div className="font-medium text-sky-100">{user.username || 'Unknown'}</div>
                        <div className="text-xs text-navy-500">{user.displayName || ''}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <div className="flex items-center space-x-2">
                      <span className="text-xl">{PLATFORM_ICONS[user.platform] || '🌐'}</span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${PLATFORM_COLORS[user.platform] || 'bg-navy-700 text-navy-300 border-navy-600'}`}>
                        {user.platform}
                      </span>
                    </div>
                  </td>
                  <td className="text-right">
                    <div className="text-lg font-bold text-gold-400">
                      {formatCurrency(user.balance)}
                    </div>
                  </td>
                  <td className="text-center">
                    <button
                      onClick={() => openAdjustModal(user)}
                      className="btn btn-secondary text-sm"
                    >
                      Adjust
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {pagination && pagination.totalPages > 1 && (
          <div className="flex justify-between items-center p-4 border-t border-navy-700">
            <span className="text-sm text-navy-400">
              Page {page} of {pagination.totalPages} ({pagination.total} total users)
            </span>
            <div className="flex space-x-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn btn-secondary text-sm disabled:opacity-50"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(p => Math.min(pagination.totalPages, p + 1))}
                disabled={page === pagination.totalPages}
                className="btn btn-secondary text-sm disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Adjust Balance Modal */}
      <FormModalBuilder
        title={`Adjust Balance - ${selectedUser?.username || ''}`}
        description={selectedUser ? `Current Balance: ${formatCurrency(selectedUser.balance)} | Platform: ${selectedUser.platform}` : ''}
        fields={adjustBalanceFields}
        isOpen={showAdjustModal && !!selectedUser}
        onClose={closeAdjustModal}
        onSubmit={handleAdjustBalance}
        submitButtonText={actionLoading ? 'Processing...' : 'Apply Adjustment'}
        cancelButtonText="Cancel"
        width="md"
        colors={waddlebotColors}
      />

      {/* Wipe Confirmation Modal */}
      <FormModalBuilder
        title="Wipe All Currency"
        description="This will permanently reset ALL user loyalty currency balances to zero. This action cannot be undone!"
        fields={wipeConfirmFields}
        isOpen={showWipeModal}
        onClose={() => setShowWipeModal(false)}
        onSubmit={(data) => {
          if (data.confirmation !== 'WIPE ALL') {
            setMessage({ type: 'error', text: 'Please type "WIPE ALL" to confirm' });
            throw new Error('Confirmation text does not match');
          }
          return handleWipeAll();
        }}
        submitButtonText={actionLoading ? 'Wiping...' : 'Confirm Wipe'}
        cancelButtonText="Cancel"
        width="md"
        colors={waddlebotColors}
      />
    </div>
  );
}

export default LoyaltyLeaderboard;
