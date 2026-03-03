const SEGMENT_COLORS = [
  'bg-emerald-500',
  'bg-sky-500',
  'bg-gold-500',
  'bg-orange-500',
  'bg-navy-600',
];

function ActivitySegmentChart({ data }) {
  if (!data) return null;

  const segments = [
    { key: 'active_24h', label: 'Active 24h', value: data.active_24h || 0 },
    { key: 'active_7d', label: 'Active 7d', value: data.active_7d || 0 },
    { key: 'active_30d', label: 'Active 30d', value: data.active_30d || 0 },
    { key: 'active_90d', label: 'Active 90d', value: data.active_90d || 0 },
    { key: 'inactive', label: 'Inactive', value: data.inactive || 0 },
  ];

  const total = segments.reduce((s, seg) => s + seg.value, 0) || 1;

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold mb-4 text-sky-100">Activity Breakdown</h2>

      {/* Stacked bar */}
      <div className="flex rounded-full h-6 overflow-hidden mb-4">
        {segments.map((seg, i) => {
          const pct = (seg.value / total) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={seg.key}
              className={`${SEGMENT_COLORS[i]} transition-all`}
              style={{ width: `${pct}%` }}
              title={`${seg.label}: ${seg.value.toLocaleString()}`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="space-y-2">
        {segments.map((seg, i) => (
          <div key={seg.key} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div className={`w-3 h-3 rounded-full ${SEGMENT_COLORS[i]}`} />
              <span className="text-sky-200">{seg.label}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-navy-400">{seg.value.toLocaleString()}</span>
              <span className="text-navy-500 text-xs w-10 text-right">
                {((seg.value / total) * 100).toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ActivitySegmentChart;
