/**
 * Vendor Discount Codes
 * Placeholder page — discount code management coming in a future release (#102)
 */
import { TicketIcon, PlusIcon } from '@heroicons/react/24/outline';

function VendorDiscountCodes() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Discount Codes</h1>
          <p className="text-navy-300 mt-1">Create and manage discount codes for your modules</p>
        </div>
        <button
          disabled
          className="flex items-center space-x-2 bg-emerald-600/40 text-white/50 px-4 py-2 rounded-lg cursor-not-allowed"
          title="Coming soon"
        >
          <PlusIcon className="w-5 h-5" />
          <span>Create Discount Code</span>
        </button>
      </div>

      {/* Coming soon content */}
      <div className="bg-navy-800 border border-navy-700 rounded-lg p-12 text-center">
        <TicketIcon className="w-16 h-16 text-navy-600 mx-auto mb-6" />
        <h2 className="text-2xl font-bold text-white mb-3">Coming Soon</h2>
        <p className="text-navy-300 max-w-md mx-auto mb-6">
          Discount codes let you offer promotional pricing on your modules — fixed amounts, percentage
          off, free trials, or limited-time bundles. You'll be able to set expiry dates, usage limits,
          and track redemptions in real time.
        </p>
        <div className="inline-block bg-sky-500/10 border border-sky-500/20 text-sky-400 text-sm px-4 py-2 rounded-lg">
          Tracked in issue&nbsp;#102 — part of the v2.2.x vendor monetization features
        </div>
      </div>

      {/* Feature preview list */}
      <div className="bg-navy-800 border border-navy-700 rounded-lg p-6">
        <h3 className="text-white font-bold mb-4">What's Coming</h3>
        <ul className="space-y-3 text-sm text-navy-300">
          {[
            'Create percentage or fixed-amount discount codes',
            'Set usage limits (total and per-user)',
            'Configure expiry dates and validity windows',
            'Restrict codes to specific modules',
            'Track redemptions and revenue impact per code',
            'Bulk generate codes for promotional campaigns',
          ].map((item) => (
            <li key={item} className="flex items-start space-x-2">
              <span className="text-navy-600 mt-0.5">•</span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export default VendorDiscountCodes;
