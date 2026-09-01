const TIER_COLORS = {
  exceptional: 'bg-emerald-500',
  very_good: 'bg-sky-500',
  good: 'bg-gold-500',
  fair: 'bg-orange-500',
  poor: 'bg-red-500',
};

function ReputationTierChart({ data }) {
  if (!data) return null;

  const { buckets = [], stats = {} } = data;
  const total = buckets.reduce((s, b) => s + (b.count || 0), 0) || 1;

  return (
    <div className="card p-6">
      <h2 className="text-lg font-semibold mb-4 text-sky-100">Reputation Distribution</h2>

      {/* Stat summary row */}
      {(stats.avg !== undefined || stats.median !== undefined) && (
        <div className="grid grid-cols-4 gap-3 mb-6">
          {[
            { label: 'Average', value: stats.avg ?? '—' },
            { label: 'Median', value: stats.median ?? '—' },
            { label: 'Min', value: stats.min ?? '—' },
            { label: 'Max', value: stats.max ?? '—' },
          ].map((s) => (
            <div key={s.label} className="bg-navy-800 rounded-lg p-3 text-center">
              <div className="text-xs text-navy-400 mb-1">{s.label}</div>
              <div className="text-lg font-bold text-sky-100">{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Bar chart */}
      <div className="space-y-3">
        {buckets.map((bucket) => {
          const pct = ((bucket.count / total) * 100).toFixed(1);
          const colorKey = bucket.label?.toLowerCase().replace(/ /g, '_');
          const colorClass = TIER_COLORS[colorKey] || 'bg-navy-500';
          return (
            <div key={bucket.label}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-sky-200">{bucket.label}</span>
                <span className="text-navy-400">{bucket.count?.toLocaleString()} ({pct}%)</span>
              </div>
              <div className="w-full bg-navy-800 rounded-full h-3">
                <div
                  className={`${colorClass} h-3 rounded-full transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
        {buckets.length === 0 && (
          <p className="text-navy-500 text-sm">No reputation data available.</p>
        )}
      </div>
    </div>
  );
}

export default ReputationTierChart;
