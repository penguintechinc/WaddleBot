function PlatformGrowthChart({ data, period = '30d', onPeriodChange }) {
  const buckets = data?.buckets || [];

  const maxUsers = Math.max(...buckets.map((b) => b.new_users || 0), 1);
  const maxCommunities = Math.max(...buckets.map((b) => b.new_communities || 0), 1);

  return (
    <div className="card p-6 mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-sky-100">Platform Growth</h2>
        <div className="flex gap-2">
          {['30d', '90d', '1y'].map((p) => (
            <button
              key={p}
              onClick={() => onPeriodChange && onPeriodChange(p)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                period === p
                  ? 'bg-sky-600 text-white'
                  : 'bg-navy-800 text-navy-400 hover:text-sky-300'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {buckets.length > 0 ? (
        <>
          {/* New Users bar chart */}
          <div className="mb-4">
            <div className="text-xs text-navy-400 mb-2 uppercase tracking-wider">New Users</div>
            <div className="flex items-end gap-1 h-32">
              {buckets.map((b, i) => (
                <div
                  key={i}
                  className="flex-1 bg-sky-500/80 hover:bg-sky-400 rounded-t transition-all relative group"
                  style={{
                    height: `${((b.new_users || 0) / maxUsers) * 100}%`,
                    minHeight: '4px',
                  }}
                >
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block bg-navy-700 text-sky-200 text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {b.label}: {b.new_users || 0} users
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* New Communities bar chart */}
          <div>
            <div className="text-xs text-navy-400 mb-2 uppercase tracking-wider">New Communities</div>
            <div className="flex items-end gap-1 h-20">
              {buckets.map((b, i) => (
                <div
                  key={i}
                  className="flex-1 bg-gold-500/80 hover:bg-gold-400 rounded-t transition-all relative group"
                  style={{
                    height: `${((b.new_communities || 0) / maxCommunities) * 100}%`,
                    minHeight: '4px',
                  }}
                >
                  <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 hidden group-hover:block bg-navy-700 text-gold-200 text-xs px-2 py-1 rounded whitespace-nowrap z-10">
                    {b.label}: {b.new_communities || 0} communities
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      ) : (
        <p className="text-navy-500 text-sm">No growth data for this period.</p>
      )}
    </div>
  );
}

export default PlatformGrowthChart;
