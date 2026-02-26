import { HashtagIcon, ChatBubbleLeftRightIcon, SpeakerWaveIcon } from '@heroicons/react/24/outline';

const CHANNEL_GROUPS = [
  { label: 'Chat Channels', type: 'chat', icon: HashtagIcon },
  { label: 'Forums', type: 'forum', icon: ChatBubbleLeftRightIcon },
  { label: 'Voice / Video', type: 'voice', icon: SpeakerWaveIcon },
];

export default function ChannelSidebar({ channels = [], activeChannelId, onSelectChannel }) {
  return (
    <div className="flex flex-col w-60 h-full bg-navy-900 border-r border-navy-700 overflow-y-auto">
      {CHANNEL_GROUPS.map(({ label, type, icon: Icon }) => {
        const group = channels.filter((ch) => ch.channelType === type);
        if (group.length === 0) return null;

        return (
          <div key={type} className="mt-4">
            <div className="px-3 mb-1">
              <span className="text-xs font-semibold text-navy-500 uppercase tracking-wider">
                {label}
              </span>
            </div>

            <ul className="space-y-0.5 px-2">
              {group.map((channel) => {
                const isActive = channel.id === activeChannelId;

                return (
                  <li key={channel.id}>
                    <button
                      type="button"
                      onClick={() => onSelectChannel?.(channel)}
                      className={[
                        'w-full flex items-center gap-2 px-2 py-1.5 rounded text-sm text-left transition-colors',
                        isActive
                          ? 'bg-gold-500/20 text-gold-400 border border-gold-500/30'
                          : 'text-navy-300 hover:bg-navy-800 hover:text-sky-300',
                      ].join(' ')}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate flex-1">{channel.name}</span>
                      {type === 'voice' && channel.participantCount > 0 && (
                        <span className="text-xs text-navy-400 shrink-0">
                          {channel.participantCount}
                        </span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </div>
  );
}
