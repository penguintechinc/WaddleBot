import {
  UserGroupIcon,
  UserIcon,
  HomeIcon,
  StarIcon,
} from '@heroicons/react/24/outline';

function PlatformSummaryCards({ data }) {
  if (!data) return null;

  const cards = [
    {
      label: 'Total Users',
      value: data.total_users?.toLocaleString() ?? 0,
      icon: UserGroupIcon,
      colorClass: 'border-l-sky-400',
      textClass: 'text-sky-100',
    },
    {
      label: 'Active Users (30d)',
      value: data.active_users_30d?.toLocaleString() ?? 0,
      icon: UserIcon,
      colorClass: 'border-l-emerald-400',
      textClass: 'text-emerald-400',
    },
    {
      label: 'Total Communities',
      value: data.total_communities?.toLocaleString() ?? 0,
      icon: HomeIcon,
      colorClass: 'border-l-gold-400',
      textClass: 'text-gold-400',
    },
    {
      label: 'Avg Reputation',
      value: data.avg_reputation ?? 0,
      icon: StarIcon,
      colorClass: 'border-l-purple-400',
      textClass: 'text-purple-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {cards.map((card) => (
        <div key={card.label} className={`card p-6 border-l-4 ${card.colorClass}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm text-navy-400">{card.label}</div>
            <card.icon className="w-5 h-5 text-navy-500" />
          </div>
          <div className={`text-3xl font-bold ${card.textClass}`}>{card.value}</div>
        </div>
      ))}
    </div>
  );
}

export default PlatformSummaryCards;
