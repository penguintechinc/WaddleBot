import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { adminApi } from '../../services/api';
import { FormModalBuilder } from '@penguintechinc/react-libs';

// WaddleBot theme colors matching the existing UI
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

const GAME_TYPES = [
  {
    id: 'slots',
    name: 'Slot Machine',
    icon: '🎰',
    color: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    description: 'Classic slot machine with customizable payouts',
  },
  {
    id: 'coinflip',
    name: 'Coin Flip',
    icon: '🪙',
    color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    description: 'Simple heads or tails betting',
  },
  {
    id: 'roulette',
    name: 'Roulette',
    icon: '🎡',
    color: 'bg-red-500/20 text-red-300 border-red-500/30',
    description: 'Roulette with multiple bet types',
  },
];

function LoyaltyGames() {
  const { communityId } = useParams();
  const [config, setConfig] = useState(null);
  const [stats, setStats] = useState(null);
  const [recentGames, setRecentGames] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [showPredictionModal, setShowPredictionModal] = useState(false);
  const [showRaffleModal, setShowRaffleModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, [communityId]);

  // Field definitions for Prediction form
  const predictionFields = useMemo(() => [
    {
      name: 'title',
      type: 'text',
      label: 'Title',
      required: true,
      placeholder: 'What will happen next?',
    },
    {
      name: 'description',
      type: 'textarea',
      label: 'Description',
      placeholder: 'Provide more context about this prediction...',
      rows: 3,
    },
    {
      name: 'options',
      type: 'multiline',
      label: 'Outcomes',
      required: true,
      placeholder: 'Enter one outcome per line (minimum 2)',
      rows: 4,
      helpText: 'Enter one possible outcome per line. At least 2 outcomes required.',
    },
    {
      name: 'end_time',
      type: 'datetime-local',
      label: 'End Time',
      required: true,
      helpText: 'When voting will close for this prediction.',
    },
  ], []);

  // Field definitions for Raffle form
  const raffleFields = useMemo(() => [
    {
      name: 'title',
      type: 'text',
      label: 'Title',
      required: true,
      placeholder: 'Weekly Points Giveaway',
    },
    {
      name: 'description',
      type: 'textarea',
      label: 'Description',
      placeholder: 'Describe the raffle and rules...',
      rows: 3,
    },
    {
      name: 'prize',
      type: 'text',
      label: 'Prize',
      required: true,
      placeholder: '10,000 loyalty points',
    },
    {
      name: 'ticket_cost',
      type: 'number',
      label: 'Ticket Cost',
      required: true,
      placeholder: '100',
      helpText: 'Points required to purchase one raffle ticket.',
    },
    {
      name: 'max_entries',
      type: 'number',
      label: 'Max Entries per User',
      placeholder: '10',
      helpText: 'Maximum tickets a user can purchase (leave empty for unlimited).',
    },
    {
      name: 'end_time',
      type: 'datetime-local',
      label: 'End Time',
      required: true,
      helpText: 'When the raffle will close and a winner will be drawn.',
    },
  ], []);

  // Placeholder handler for creating a prediction (closes modal for now)
  const handleCreatePrediction = async (data) => {
    // TODO: Implement API call to create prediction
    // await adminApi.createPrediction(communityId, {
    //   title: data.title,
    //   description: data.description,
    //   options: data.options, // multiline returns array of strings
    //   end_time: data.end_time,
    // });
    console.log('Create prediction:', data);
    setMessage({ type: 'success', text: 'Prediction creation not yet implemented' });
    setShowPredictionModal(false);
  };

  // Placeholder handler for creating a raffle (closes modal for now)
  const handleCreateRaffle = async (data) => {
    // TODO: Implement API call to create raffle
    // await adminApi.createRaffle(communityId, {
    //   title: data.title,
    //   description: data.description,
    //   prize: data.prize,
    //   ticket_cost: parseInt(data.ticket_cost, 10),
    //   max_entries: data.max_entries ? parseInt(data.max_entries, 10) : null,
    //   end_time: data.end_time,
    // });
    console.log('Create raffle:', data);
    setMessage({ type: 'success', text: 'Raffle creation not yet implemented' });
    setShowRaffleModal(false);
  };

  async function fetchData() {
    setLoading(true);
    try {
      const [configRes, statsRes, recentRes] = await Promise.all([
        adminApi.getLoyaltyGamesConfig(communityId),
        adminApi.getLoyaltyGamesStats(communityId),
        adminApi.getLoyaltyGamesRecent(communityId, { limit: 50 }),
      ]);

      if (configRes.data.success) {
        setConfig(configRes.data.config);
      }
      if (statsRes.data.success) {
        setStats(statsRes.data.stats);
      }
      if (recentRes.data.success) {
        setRecentGames(recentRes.data.games || []);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
      setMessage({ type: 'error', text: 'Failed to load loyalty games data' });
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveConfig() {
    setSaving(true);
    setMessage(null);
    try {
      await adminApi.updateLoyaltyGamesConfig(communityId, config);
      setMessage({ type: 'success', text: 'Game configuration saved' });
      await fetchData();
    } catch (err) {
      console.error('Failed to save config:', err);
      setMessage({
        type: 'error',
        text: err.response?.data?.error?.message || 'Failed to save configuration',
      });
    } finally {
      setSaving(false);
    }
  }

  function updateGameConfig(gameId, key, value) {
    setConfig({
      ...config,
      games: {
        ...config.games,
        [gameId]: {
          ...(config.games?.[gameId] || {}),
          [key]: value,
        },
      },
    });
  }

  function formatNumber(num) {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toLocaleString();
  }

  function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString();
  }

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  if (!config || !stats) {
    return (
      <div className="text-center py-12 text-red-400">
        Failed to load loyalty games data
      </div>
    );
  }

  const houseProfit = (stats.total_wagered || 0) - (stats.total_payouts || 0);
  const houseProfitPercent = stats.total_wagered > 0
    ? ((houseProfit / stats.total_wagered) * 100).toFixed(2)
    : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-sky-100">Loyalty Minigames</h1>
          <p className="text-navy-400 mt-1">
            Configure and monitor gambling games and community events
          </p>
        </div>
        <button
          onClick={handleSaveConfig}
          disabled={saving}
          className="btn btn-primary disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {message && (
        <div
          className={`mb-6 p-4 rounded-lg border ${
            message.type === 'success'
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : 'bg-red-500/20 text-red-300 border-red-500/30'
          }`}
        >
          {message.text}
          <button onClick={() => setMessage(null)} className="float-right">
            ×
          </button>
        </div>
      )}

      <div className="space-y-6">
        {/* Global Stats */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Total Games</div>
            <div className="text-2xl font-bold text-sky-100">
              {formatNumber(stats.total_games || 0)}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Total Wagered</div>
            <div className="text-2xl font-bold text-purple-300">
              {formatNumber(stats.total_wagered || 0)}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Total Payouts</div>
            <div className="text-2xl font-bold text-yellow-300">
              {formatNumber(stats.total_payouts || 0)}
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">House Profit</div>
            <div
              className={`text-2xl font-bold ${
                houseProfit >= 0 ? 'text-emerald-300' : 'text-red-300'
              }`}
            >
              {houseProfit >= 0 ? '+' : ''}
              {formatNumber(houseProfit)}
            </div>
            <div className="text-xs text-navy-500 mt-1">
              {houseProfitPercent}% edge
            </div>
          </div>
          <div className="card p-4">
            <div className="text-sm text-navy-400 mb-1">Most Popular</div>
            <div className="text-lg font-bold text-sky-100">
              {stats.most_popular_game
                ? GAME_TYPES.find((g) => g.id === stats.most_popular_game)?.icon || '🎮'
                : '—'}
            </div>
            <div className="text-xs text-navy-500 mt-1">
              {stats.most_popular_game || 'None'}
            </div>
          </div>
        </div>

        {/* Game Configuration Cards */}
        <div className="grid md:grid-cols-3 gap-4">
          {/* Slots */}
          <div className={`card p-6 border ${GAME_TYPES[0].color}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{GAME_TYPES[0].icon}</span>
                <div>
                  <div className="font-bold text-sky-100">{GAME_TYPES[0].name}</div>
                  <div className="text-xs text-navy-400">{GAME_TYPES[0].description}</div>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.games?.slots?.enabled || false}
                  onChange={(e) => updateGameConfig('slots', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-navy-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-purple-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-500"></div>
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  House Edge %
                </label>
                <div className="flex items-center gap-3">
                  <input
                    type="range"
                    min="1"
                    max="20"
                    step="0.5"
                    value={config.games?.slots?.house_edge || 5}
                    onChange={(e) =>
                      updateGameConfig('slots', 'house_edge', parseFloat(e.target.value))
                    }
                    disabled={!config.games?.slots?.enabled}
                    className="flex-1 h-2 bg-navy-700 rounded-lg appearance-none cursor-pointer disabled:opacity-50"
                  />
                  <span className="w-12 text-center text-sky-100 font-bold">
                    {config.games?.slots?.house_edge || 5}%
                  </span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Max Payout Multiplier
                </label>
                <input
                  type="number"
                  min="2"
                  max="1000"
                  value={config.games?.slots?.max_payout_multiplier || 100}
                  onChange={(e) =>
                    updateGameConfig('slots', 'max_payout_multiplier', parseInt(e.target.value) || 100)
                  }
                  disabled={!config.games?.slots?.enabled}
                  className="w-full px-3 py-2 bg-navy-700 border border-navy-600 rounded-lg text-sky-100 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 disabled:opacity-50"
                />
              </div>
            </div>
          </div>

          {/* Coinflip */}
          <div className={`card p-6 border ${GAME_TYPES[1].color}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{GAME_TYPES[1].icon}</span>
                <div>
                  <div className="font-bold text-sky-100">{GAME_TYPES[1].name}</div>
                  <div className="text-xs text-navy-400">{GAME_TYPES[1].description}</div>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.games?.coinflip?.enabled || false}
                  onChange={(e) => updateGameConfig('coinflip', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-navy-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-yellow-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-yellow-500"></div>
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Payout Multiplier
                </label>
                <input
                  type="number"
                  min="1.5"
                  max="2.0"
                  step="0.05"
                  value={config.games?.coinflip?.payout_multiplier || 1.95}
                  onChange={(e) =>
                    updateGameConfig('coinflip', 'payout_multiplier', parseFloat(e.target.value) || 1.95)
                  }
                  disabled={!config.games?.coinflip?.enabled}
                  className="w-full px-3 py-2 bg-navy-700 border border-navy-600 rounded-lg text-sky-100 focus:border-yellow-500 focus:ring-1 focus:ring-yellow-500 disabled:opacity-50"
                />
                <p className="text-xs text-navy-500 mt-1">
                  2.0 = no house edge, 1.95 = 2.5% edge
                </p>
              </div>
            </div>
          </div>

          {/* Roulette */}
          <div className={`card p-6 border ${GAME_TYPES[2].color}`}>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-3xl">{GAME_TYPES[2].icon}</span>
                <div>
                  <div className="font-bold text-sky-100">{GAME_TYPES[2].name}</div>
                  <div className="text-xs text-navy-400">{GAME_TYPES[2].description}</div>
                </div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.games?.roulette?.enabled || false}
                  onChange={(e) => updateGameConfig('roulette', 'enabled', e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-navy-700 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-red-500 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-500"></div>
              </label>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-navy-300 mb-2">
                  Enabled Bet Types
                </label>
                <div className="space-y-2">
                  {['color', 'number', 'dozen', 'column'].map((betType) => (
                    <label key={betType} className="flex items-center gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={
                          config.games?.roulette?.bet_types?.[betType] || false
                        }
                        onChange={(e) => {
                          const betTypes = config.games?.roulette?.bet_types || {};
                          updateGameConfig('roulette', 'bet_types', {
                            ...betTypes,
                            [betType]: e.target.checked,
                          });
                        }}
                        disabled={!config.games?.roulette?.enabled}
                        className="w-4 h-4 rounded border-navy-600 text-red-500 focus:ring-red-500 disabled:opacity-50"
                      />
                      <span className="text-navy-300 capitalize">{betType}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Predictions Section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-sky-100">Predictions</h2>
              <p className="text-sm text-navy-400">
                Community predictions for events and outcomes
              </p>
            </div>
            <button
              onClick={() => setShowPredictionModal(true)}
              className="btn btn-primary"
            >
              Create Prediction
            </button>
          </div>

          {stats.active_predictions?.length > 0 ? (
            <div className="space-y-3">
              {stats.active_predictions.map((prediction) => (
                <div
                  key={prediction.id}
                  className="flex items-center justify-between p-4 bg-navy-800 rounded-lg"
                >
                  <div>
                    <div className="font-medium text-sky-100">{prediction.title}</div>
                    <div className="text-sm text-navy-400">
                      {prediction.total_entries} entries • {formatNumber(prediction.total_wagered)} points
                    </div>
                  </div>
                  <button className="btn btn-sm btn-secondary">Resolve</button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-navy-400">
              No active predictions
            </div>
          )}
        </div>

        {/* Raffles Section */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-semibold text-sky-100">Raffles</h2>
              <p className="text-sm text-navy-400">
                Community raffles and giveaways
              </p>
            </div>
            <button
              onClick={() => setShowRaffleModal(true)}
              className="btn btn-primary"
            >
              Create Raffle
            </button>
          </div>

          {stats.active_raffles?.length > 0 ? (
            <div className="space-y-3">
              {stats.active_raffles.map((raffle) => (
                <div
                  key={raffle.id}
                  className="flex items-center justify-between p-4 bg-navy-800 rounded-lg"
                >
                  <div>
                    <div className="font-medium text-sky-100">{raffle.title}</div>
                    <div className="text-sm text-navy-400">
                      {raffle.total_entries} entries • Prize: {raffle.prize}
                    </div>
                  </div>
                  <button className="btn btn-sm btn-secondary">Draw Winner</button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-navy-400">
              No active raffles
            </div>
          )}
        </div>

        {/* Recent Games Table */}
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-sky-100 mb-4">Recent Game Results</h2>
          {recentGames.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-navy-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-navy-400">
                      Time
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-navy-400">
                      User
                    </th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-navy-400">
                      Game
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-navy-400">
                      Bet
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-medium text-navy-400">
                      Result
                    </th>
                    <th className="text-right py-3 px-4 text-sm font-medium text-navy-400">
                      Payout
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {recentGames.map((game, idx) => {
                    const gameType = GAME_TYPES.find((g) => g.id === game.game_type);
                    const isWin = game.payout > game.bet_amount;
                    return (
                      <tr
                        key={idx}
                        className="border-b border-navy-800 hover:bg-navy-800/50 transition-colors"
                      >
                        <td className="py-3 px-4 text-sm text-navy-300">
                          {formatTimestamp(game.timestamp)}
                        </td>
                        <td className="py-3 px-4 text-sm text-sky-100">
                          {game.username}
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{gameType?.icon || '🎮'}</span>
                            <span className="text-sm text-navy-300">
                              {gameType?.name || game.game_type}
                            </span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-sm text-right text-navy-300">
                          {formatNumber(game.bet_amount)}
                        </td>
                        <td className="py-3 px-4 text-center">
                          <span
                            className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                              isWin
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-red-500/20 text-red-300'
                            }`}
                          >
                            {isWin ? 'Win' : 'Loss'}
                          </span>
                        </td>
                        <td
                          className={`py-3 px-4 text-sm text-right font-medium ${
                            isWin ? 'text-emerald-300' : 'text-red-300'
                          }`}
                        >
                          {isWin ? '+' : '-'}
                          {formatNumber(Math.abs(game.payout - game.bet_amount))}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-8 text-navy-400">
              No recent game activity
            </div>
          )}
        </div>
      </div>

      {/* Create Prediction Modal */}
      <FormModalBuilder
        title="Create Prediction"
        fields={predictionFields}
        isOpen={showPredictionModal}
        onClose={() => setShowPredictionModal(false)}
        onSubmit={handleCreatePrediction}
        submitButtonText="Create Prediction"
        cancelButtonText="Cancel"
        width="lg"
        colors={waddlebotColors}
      />

      {/* Create Raffle Modal */}
      <FormModalBuilder
        title="Create Raffle"
        fields={raffleFields}
        isOpen={showRaffleModal}
        onClose={() => setShowRaffleModal(false)}
        onSubmit={handleCreateRaffle}
        submitButtonText="Create Raffle"
        cancelButtonText="Cancel"
        width="lg"
        colors={waddlebotColors}
      />
    </div>
  );
}

export default LoyaltyGames;
