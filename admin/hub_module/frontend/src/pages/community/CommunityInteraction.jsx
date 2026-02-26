import { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { io } from 'socket.io-client';
import { interactionApi } from '../../services/api';
import ChannelSidebar from '../../components/interaction/ChannelSidebar';
import ChatView from '../../components/interaction/ChatView';
import ForumView from '../../components/interaction/ForumView';
import VoiceView from '../../components/interaction/VoiceView';
import { ArrowPathIcon, ChatBubbleLeftRightIcon } from '@heroicons/react/24/outline';

function CommunityInteraction() {
  const { communityId, channelId } = useParams();
  const navigate = useNavigate();
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Socket.IO connection — shared across chat channels
  const socket = useMemo(() => {
    const token = localStorage.getItem('token');
    return io(import.meta.env.VITE_API_URL || window.location.origin, {
      auth: { token },
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });
  }, []);

  useEffect(() => {
    return () => { socket.disconnect(); };
  }, [socket]);

  // Load channels
  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const res = await interactionApi.getChannels(communityId);
        setChannels(res.data?.channels || []);
      } catch (err) {
        console.error('Failed to load channels:', err);
        setError('Failed to load channels');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [communityId]);

  // Resolve active channel
  const activeChannel = channelId
    ? channels.find(c => c.id === parseInt(channelId, 10))
    : channels[0] || null;

  const handleSelectChannel = (ch) => {
    navigate(`/community/${communityId}/interact/${ch.id}`);
  };

  // Auto-navigate to first channel when loaded
  useEffect(() => {
    if (!channelId && channels.length) {
      navigate(`/community/${communityId}/interact/${channels[0].id}`, { replace: true });
    }
  }, [channelId, channels, communityId, navigate]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <ArrowPathIcon className="w-6 h-6 text-navy-400 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!channels.length) {
    return (
      <div className="text-center py-20">
        <ChatBubbleLeftRightIcon className="w-12 h-12 text-navy-600 mx-auto mb-4" />
        <p className="text-navy-400 text-lg">No channels yet</p>
        <p className="text-navy-500 text-sm mt-1">Ask a community admin to create channels.</p>
      </div>
    );
  }

  const renderContent = () => {
    if (!activeChannel) return null;

    switch (activeChannel.channelType) {
      case 'chat':
        return <ChatView channel={{ ...activeChannel, communityId }} socket={socket} />;
      case 'forum':
        return <ForumView channel={{ ...activeChannel, communityId }} />;
      case 'voice':
        return <VoiceView channel={{ ...activeChannel, communityId }} />;
      default:
        return <div className="text-navy-400 p-4">Unknown channel type</div>;
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] -m-6">
      <ChannelSidebar
        channels={channels}
        activeChannelId={activeChannel?.id}
        onSelectChannel={handleSelectChannel}
      />
      <div className="flex-1 flex flex-col min-w-0">
        {renderContent()}
      </div>
    </div>
  );
}

export default CommunityInteraction;
