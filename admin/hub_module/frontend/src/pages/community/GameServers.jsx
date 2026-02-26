import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ArrowPathIcon, SignalIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { rconApi } from '../../services/api';
import GameTypeBadge from '../../components/GameTypeBadge';

const SERVER_TYPE_LABELS = {
  rcon: 'Game Server',
  mumble: 'Mumble',
  teamspeak: 'TeamSpeak',
  status_only: 'Status Monitor',
};

function GameServers() {
  const { communityId } = useParams();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statuses, setStatuses] = useState({});

  const loadServers = useCallback(async () => {
    try {
      setLoading(true);
      setError('');
      const res = await rconApi.listInfo(communityId);
      setServers(res.data?.servers || []);
    } catch (err) {
      console.error('Failed to load servers:', err);
      setError('Failed to load game servers.');
    } finally {
      setLoading(false);
    }
  }, [communityId]);

  useEffect(() => { loadServers(); }, [loadServers]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(loadServers, 30000);
    return () => clearInterval(interval);
  }, [loadServers]);

  // Fetch status for each server
  useEffect(() => {
    if (!servers.length) return;
    servers.forEach(async (srv) => {
      try {
        const res = await rconApi.getServerStatus(communityId, srv.id);
        setStatuses((prev) => ({ ...prev, [srv.id]: res.data?.data || res.data }));
      } catch {
        setStatuses((prev) => ({ ...prev, [srv.id]: { online: false } }));
      }
    });
  }, [servers, communityId]);

  if (loading && !servers.length) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-6 h-6 text-navy-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sky-100">Game Servers</h1>
          <p className="text-navy-400 text-sm mt-1">Connect to community game and voice servers</p>
        </div>
        <button
          onClick={loadServers}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-navy-300 hover:text-sky-300 bg-navy-800 hover:bg-navy-700 rounded-lg border border-navy-600 transition-colors"
        >
          <ArrowPathIcon className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {!servers.length && !loading && (
        <div className="text-center py-16">
          <SignalIcon className="w-12 h-12 text-navy-600 mx-auto mb-3" />
          <p className="text-navy-400">No game servers available yet.</p>
        </div>
      )}

      {/* Server cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {servers.map((srv) => {
          const status = statuses[srv.id];
          const isOnline = status?.online || status?.success;
          const playerCount = status?.clients_online || status?.users?.length || null;

          return (
            <div
              key={srv.id}
              className="bg-navy-900 border border-navy-700 rounded-xl p-5 hover:border-navy-600 transition-colors"
            >
              {/* Top: badge + status dot */}
              <div className="flex items-start justify-between mb-3">
                <GameTypeBadge type={srv.game_type} size="md" />
                <span className="flex items-center gap-1.5">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      isOnline ? 'bg-green-400 shadow-green-400/50 shadow-sm' : 'bg-red-400'
                    }`}
                  />
                  <span className={`text-xs font-medium ${isOnline ? 'text-green-400' : 'text-red-400'}`}>
                    {isOnline ? 'Online' : 'Offline'}
                  </span>
                </span>
              </div>

              {/* Server name */}
              <h3 className="text-lg font-semibold text-sky-100 mb-1">
                {srv.display_name || srv.game_name}
              </h3>

              {/* Server type label */}
              <p className="text-xs text-navy-500 mb-3">
                {SERVER_TYPE_LABELS[srv.server_type] || srv.server_type}
              </p>

              {/* Stats row */}
              <div className="flex items-center gap-4 text-sm">
                {playerCount !== null && (
                  <span className="flex items-center gap-1 text-navy-300">
                    <UserGroupIcon className="w-4 h-4" />
                    {playerCount} online
                  </span>
                )}
                {srv.game_port && (
                  <span className="text-navy-500 font-mono text-xs">
                    :{srv.game_port}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default GameServers;
