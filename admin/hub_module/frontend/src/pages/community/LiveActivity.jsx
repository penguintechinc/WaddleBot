/**
 * Live Activity Page
 * Real-time feed of incoming platform messages and the bot's replies,
 * streamed via SSE from hub-api. Backfills via the list endpoint on mount,
 * then appends live events as they arrive.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { SignalIcon } from '@heroicons/react/24/outline';
import api from '../../services/api';
import { getPlatformConfig } from '../../utils/platformConfig';

const MAX_EVENTS = 100;

function formatTime(isoString) {
  try {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '';
  }
}

function ActivityRow({ event }) {
  const platform = getPlatformConfig(event.platform);

  return (
    <div className="bg-navy-800 border border-navy-700 rounded-lg px-4 py-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${platform.color}`}
          >
            <span aria-hidden="true">{platform.icon}</span>
            {platform.label}
          </span>
          <span className="text-sky-100 font-medium text-sm">
            {event.actor || 'Unknown user'}
          </span>
        </div>
        <span className="text-navy-500 text-xs">{formatTime(event.occurred_at)}</span>
      </div>

      {event.message_in && (
        <p className="text-navy-200 text-sm pl-1 border-l-2 border-navy-600">
          {event.message_in}
        </p>
      )}

      {event.reply_out && (
        <p className="text-gold-300 text-sm pl-1 border-l-2 border-gold-500/50">
          <span aria-hidden="true">🐧</span> Waddles: {event.reply_out}
        </p>
      )}
    </div>
  );
}

export default function LiveActivity() {
  const { communityId } = useParams();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connectionState, setConnectionState] = useState('connecting'); // connecting | live | reconnecting

  const eventSourceRef = useRef(null);
  const seenIdsRef = useRef(new Set());

  const addEvent = useCallback((event) => {
    if (event?.id == null || seenIdsRef.current.has(event.id)) return;
    seenIdsRef.current.add(event.id);
    setEvents((prev) => {
      const next = [event, ...prev].slice(0, MAX_EVENTS);
      // Trim the seen-id set to match what's still displayed to avoid
      // unbounded growth over a long-running demo session.
      seenIdsRef.current = new Set(next.map((e) => e.id));
      return next;
    });
  }, []);

  // Backfill on mount
  useEffect(() => {
    let cancelled = false;

    async function loadBackfill() {
      try {
        setLoading(true);
        setError(null);
        const response = await api.get(
          `/api/v1/community/${communityId}/live-activity`,
          { params: { limit: 50 } }
        );
        if (cancelled) return;
        const items = response.data?.data ?? response.data ?? [];
        const list = Array.isArray(items) ? items : [];
        seenIdsRef.current = new Set(list.map((e) => e.id));
        setEvents(list);
      } catch (err) {
        console.error('[LiveActivity] Backfill failed', {
          status: err.response?.status,
        });
        if (!cancelled) setError('Failed to load recent activity');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadBackfill();
    return () => {
      cancelled = true;
    };
  }, [communityId]);

  // Live stream via native EventSource (same-origin, cookies flow through
  // the Express proxy automatically — no socket.io, this only reaches
  // hub-api, not the legacy backend).
  useEffect(() => {
    const url = `/api/v1/community/${communityId}/live-activity/stream`;
    const source = new EventSource(url, { withCredentials: true });
    eventSourceRef.current = source;
    setConnectionState('connecting');

    source.onopen = () => {
      console.debug('[LiveActivity] Stream connected', { communityId });
      setConnectionState('live');
    };

    source.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data);
        addEvent(event);
      } catch (err) {
        console.error('[LiveActivity] Failed to parse event', { error: err.message });
      }
    };

    source.onerror = () => {
      // EventSource auto-reconnects; readyState CONNECTING means it's
      // retrying, CLOSED means it gave up (rare, only on non-network errors).
      if (source.readyState === EventSource.CLOSED) {
        setConnectionState('reconnecting');
      } else {
        setConnectionState('reconnecting');
      }
    };

    return () => {
      source.close();
      eventSourceRef.current = null;
    };
  }, [communityId, addEvent]);

  const statusConfig = {
    connecting: { label: 'Connecting…', dot: 'bg-navy-400 animate-pulse' },
    live: { label: 'Live', dot: 'bg-emerald-400' },
    reconnecting: { label: 'Reconnecting…', dot: 'bg-amber-400 animate-pulse' },
  }[connectionState];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-sky-100 flex items-center gap-2">
            <SignalIcon className="w-6 h-6 text-gold-400" />
            Live Activity
          </h1>
          <p className="text-navy-400 mt-1">
            Real-time Discord and Twitch messages and Waddles&apos; replies
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 bg-navy-800 border border-navy-700 rounded-full">
          <span className={`w-2 h-2 rounded-full ${statusConfig.dot}`} aria-hidden="true" />
          <span className="text-sm text-navy-300">{statusConfig.label}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
          <span className="text-red-400">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gold-400" />
        </div>
      ) : events.length === 0 ? (
        <div className="bg-navy-800 border border-navy-700 rounded-lg p-12 text-center">
          <SignalIcon className="w-12 h-12 text-navy-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-sky-100 mb-2">No Activity Yet</h3>
          <p className="text-navy-400">
            Messages will appear here as they come in from connected platforms.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {events.map((event) => (
            <ActivityRow key={event.id} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
