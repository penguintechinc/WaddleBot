import { useState, useEffect } from 'react';
import { ChevronDown, AlertCircle } from 'lucide-react';
import { kongApi } from '../../services/api';
import KongServices from './kong/KongServices';
import KongRoutes from './kong/KongRoutes';
import KongPlugins from './kong/KongPlugins';
import KongConsumers from './kong/KongConsumers';
import KongUpstreams from './kong/KongUpstreams';
import KongCertificates from './kong/KongCertificates';
import KongRateLimiting from './kong/KongRateLimiting';

const TABS = [
  { id: 'services', label: 'Services', icon: '🔧' },
  { id: 'routes', label: 'Routes', icon: '🛣️' },
  { id: 'plugins', label: 'Plugins', icon: '🔌' },
  { id: 'consumers', label: 'Consumers', icon: '👥' },
  { id: 'upstreams', label: 'Upstreams', icon: '⬆️' },
  { id: 'certificates', label: 'Certificates', icon: '🔐' },
  { id: 'rate-limiting', label: 'Rate Limiting', icon: '⏱️' },
];

export default function SuperAdminKongGateway() {
  const [activeTab, setActiveTab] = useState('services');
  const [kongAvailable, setKongAvailable] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkKongHealth();
  }, []);

  const checkKongHealth = async () => {
    try {
      setLoading(true);
      const response = await kongApi.getKongHealth();
      setKongAvailable(response.data?.available || false);
    } catch (error) {
      setKongAvailable(false);
    } finally {
      setLoading(false);
    }
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'services':
        return <KongServices />;
      case 'routes':
        return <KongRoutes />;
      case 'plugins':
        return <KongPlugins />;
      case 'consumers':
        return <KongConsumers />;
      case 'upstreams':
        return <KongUpstreams />;
      case 'certificates':
        return <KongCertificates />;
      case 'rate-limiting':
        return <KongRateLimiting />;
      default:
        return <KongServices />;
    }
  };

  return (
    <div className="min-h-screen bg-navy-950 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-sky-400 mb-2">Kong Gateway</h1>
          <p className="text-gray-400">Manage API gateway configuration, routes, plugins, and security</p>
        </div>

        {/* Kong Unavailable Warning */}
        {!loading && !kongAvailable && (
          <div className="mb-8 bg-amber-900/20 border border-amber-500 rounded-lg p-4 flex items-start gap-4">
            <AlertCircle className="text-amber-400 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <h3 className="text-amber-400 font-semibold mb-1">Kong Gateway Not Available</h3>
              <p className="text-amber-200 text-sm">
                Kong Gateway is not deployed or not reachable. Please verify that Kong is running and the KONG_ADMIN_URL environment variable is configured correctly. You can still view this interface, but Kong-related operations will not work until the gateway is available.
              </p>
              <button
                onClick={checkKongHealth}
                className="mt-3 px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-sm rounded transition-colors"
              >
                Retry Connection
              </button>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="mb-6 border-b border-navy-800 flex overflow-x-auto">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-6 py-4 font-semibold whitespace-nowrap border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-sky-400 text-sky-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
              disabled={!loading && !kongAvailable}
              title={!loading && !kongAvailable ? 'Kong Gateway is not available' : ''}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}
