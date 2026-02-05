import { useState, useEffect } from 'react';
import { publicApi } from '../../services/api';

function LiveStreamsPage() {
  const [streams, setStreams] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStreams() {
      try {
        const response = await publicApi.getLiveStreams({ limit: 20 });
        setStreams(response.data.streams);
      } catch (err) {
        console.error('Failed to fetch streams:', err);
      } finally {
        setLoading(false);
      }
    }
    fetchStreams();
    const interval = setInterval(fetchStreams, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gold-400"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Live Streams</h1>
          <p className="text-navy-400">Currently live from Waddles communities</p>
        </div>
        <div className="flex items-center space-x-2 text-red-400">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
          </span>
          <span className="font-medium">{streams.length} Live</span>
        </div>
      </div>

      {streams.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-6xl mb-4">📺</div>
          <h2 className="text-xl font-semibold mb-2 text-sky-100">No Streams Live</h2>
          <p className="text-navy-400">Check back later for live content</p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {streams.map((stream) => (
            <a
              key={stream.entityId}
              href={`https://twitch.tv/${stream.channelName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="card overflow-hidden hover:border-sky-500 transition-all group"
            >
              <div className="relative aspect-video bg-navy-800">
                {stream.thumbnailUrl ? (
                  <img
                    src={stream.thumbnailUrl.replace('{width}', '440').replace('{height}', '248')}
                    alt={stream.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-4xl">📺</span>
                  </div>
                )}
                <div className="absolute top-2 left-2 bg-red-600 text-white text-xs font-medium px-2 py-1 rounded">
                  LIVE
                </div>
                <div className="absolute bottom-2 left-2 bg-black/75 text-white text-xs px-2 py-1 rounded">
                  {stream.viewerCount.toLocaleString()} viewers
                </div>
              </div>
              <div className="p-4">
                <h3 className="font-semibold truncate text-sky-100 group-hover:text-gold-400 transition-colors">
                  {stream.channelName}
                </h3>
                <p className="text-sm text-navy-400 truncate">{stream.title || 'No title'}</p>
                {stream.game && (
                  <p className="text-xs text-navy-500 mt-1">{stream.game}</p>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

export default LiveStreamsPage;
