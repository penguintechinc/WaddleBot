/**
 * Vendor Request Footer
 * Shows offer to become a vendor for non-vendor logged-in users
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { SparklesIcon, XMarkIcon } from '@heroicons/react/24/outline';

function VendorRequestFooter() {
  const { user } = useAuth();
  const [dismissed, setDismissed] = useState(localStorage.getItem('vendor-request-dismissed') === 'true');

  // Only show for logged-in non-vendors
  if (!user || user.isVendor || dismissed) {
    return null;
  }

  const handleDismiss = () => {
    setDismissed(true);
    localStorage.setItem('vendor-request-dismissed', 'true');
  };

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-4 py-4 shadow-lg">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <SparklesIcon className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1">
            <p className="font-medium">Become a Vendor</p>
            <p className="text-sm text-purple-100">Submit your first module to the Waddles marketplace</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            to="/vendor/request"
            className="bg-white text-purple-600 hover:bg-purple-50 px-4 py-2 rounded-lg font-medium transition-colors whitespace-nowrap"
          >
            Request Vendor Status
          </Link>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-purple-700 rounded-lg transition-colors"
            title="Dismiss"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default VendorRequestFooter;
