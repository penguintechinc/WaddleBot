import PropTypes from 'prop-types';

function CommunityStatsWidget({ community, recentActivity, streams }) {
  const stats = [
    { label: 'Members', value: community?.memberCount?.toLocaleString() ?? '—' },
    { label: 'Live Streams', value: streams?.length ?? 0 },
    { label: 'Recent Activity', value: recentActivity?.length ?? 0 },
  ];
  return (
    <div className="card">
      <div className="card-header">
        <h2 className="font-semibold text-sky-100">Community Stats</h2>
      </div>
      <div className="p-4 grid grid-cols-3 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="text-center">
            <div className="text-2xl font-bold text-gold-400">{s.value}</div>
            <div className="text-xs text-navy-400 mt-1">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

CommunityStatsWidget.propTypes = {
  community: PropTypes.shape({ memberCount: PropTypes.number }),
  recentActivity: PropTypes.array,
  streams: PropTypes.array,
};

export default CommunityStatsWidget;
