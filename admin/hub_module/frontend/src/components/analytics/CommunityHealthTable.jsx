import { useState } from 'react';

function healthScoreClass(score) {
  if (score === null || score === undefined) return 'bg-navy-700 text-navy-300';
  if (score >= 75) return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (score >= 50) return 'bg-gold-500/20 text-gold-300 border border-gold-500/30';
  return 'bg-red-500/20 text-red-300 border border-red-500/30';
}

function botGradeClass(grade) {
  if (!grade) return 'bg-navy-700 text-navy-300';
  const g = grade.toUpperCase();
  if (g === 'A') return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
  if (g === 'B') return 'bg-sky-500/20 text-sky-300 border border-sky-500/30';
  if (g === 'C') return 'bg-gold-500/20 text-gold-300 border border-gold-500/30';
  if (g === 'D') return 'bg-orange-500/20 text-orange-300 border border-orange-500/30';
  return 'bg-red-500/20 text-red-300 border border-red-500/30';
}

function CommunityHealthTable({ data }) {
  const [sortKey, setSortKey] = useState('health_score');
  const [sortDir, setSortDir] = useState('desc');

  if (!data || data.length === 0) {
    return (
      <div className="card p-6">
        <h2 className="text-lg font-semibold mb-4 text-sky-100">Community Health</h2>
        <p className="text-navy-500 text-sm">No community health data available.</p>
      </div>
    );
  }

  const toggleSort = (key) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...data].sort((a, b) => {
    const aVal = a[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity);
    const bVal = b[sortKey] ?? (sortDir === 'asc' ? Infinity : -Infinity);
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const SortIcon = ({ col }) => {
    if (sortKey !== col) return <span className="text-navy-600 ml-1">↕</span>;
    return <span className="text-gold-400 ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  const thClass = 'px-4 py-3 text-left text-xs font-semibold text-gold-400 uppercase cursor-pointer hover:text-gold-300 select-none';

  return (
    <div className="card overflow-hidden">
      <div className="p-6 pb-0">
        <h2 className="text-lg font-semibold mb-4 text-sky-100">Community Health</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-navy-900 border-b border-navy-700">
            <tr>
              <th className={thClass} onClick={() => toggleSort('name')}>
                Community <SortIcon col="name" />
              </th>
              <th className={thClass} onClick={() => toggleSort('member_count')}>
                Members <SortIcon col="member_count" />
              </th>
              <th className={thClass} onClick={() => toggleSort('health_score')}>
                Health <SortIcon col="health_score" />
              </th>
              <th className={thClass} onClick={() => toggleSort('bot_score_grade')}>
                Bot Grade <SortIcon col="bot_score_grade" />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-navy-700">
            {sorted.map((community) => (
              <tr key={community.id} className="hover:bg-navy-700/50 transition-colors">
                <td className="px-4 py-3 text-sm text-sky-100 font-medium">
                  {community.name || `Community #${community.id}`}
                </td>
                <td className="px-4 py-3 text-sm text-navy-300">
                  {community.member_count?.toLocaleString() ?? '—'}
                </td>
                <td className="px-4 py-3 text-sm">
                  {community.health_score !== null && community.health_score !== undefined ? (
                    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${healthScoreClass(community.health_score)}`}>
                      {community.health_score}
                    </span>
                  ) : (
                    <span className="text-navy-500">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm">
                  {community.bot_score_grade ? (
                    <span className={`inline-block px-2 py-1 rounded text-xs font-bold ${botGradeClass(community.bot_score_grade)}`}>
                      {community.bot_score_grade.toUpperCase()}
                    </span>
                  ) : (
                    <span className="text-navy-500">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default CommunityHealthTable;
