import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './VendorSubmissionForm.css';

const SCOPES = [
  { id: 'read_chat', name: 'Read Chat Messages', risk: 'low' },
  { id: 'send_message', name: 'Send Messages', risk: 'medium' },
  { id: 'read_profile', name: 'Read User Profiles', risk: 'low' },
  { id: 'read_viewers', name: 'Read Viewer List', risk: 'low' },
  { id: 'modify_settings', name: 'Modify Community Settings', risk: 'high' },
  { id: 'control_music', name: 'Control Music Player', risk: 'medium' },
  { id: 'read_music', name: 'Read Music Queue', risk: 'low' },
  { id: 'read_permissions', name: 'Read Permissions', risk: 'medium' },
  { id: 'modify_permissions', name: 'Modify Permissions', risk: 'critical' },
  { id: 'delete_data', name: 'Delete Community Data', risk: 'critical' },
];

const PAYMENT_METHODS = [
  { id: 'paypal', name: 'PayPal' },
  { id: 'stripe', name: 'Stripe' },
  { id: 'check', name: 'Check by Mail' },
  { id: 'bank_transfer', name: 'Bank Transfer' },
  { id: 'other', name: 'Other' },
];

const MODULE_CATEGORIES = [
  { id: 'interactive', name: 'Interactive (user responses)' },
  { id: 'pushing', name: 'Pushing (external systems)' },
  { id: 'security', name: 'Security (moderation)' },
  { id: 'marketplace', name: 'Marketplace Integration' },
  { id: 'other', name: 'Other' },
];

export default function VendorSubmissionForm() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [submissionId, setSubmissionId] = useState('');

  const [formData, setFormData] = useState({
    // Vendor Info
    vendorName: '',
    vendorEmail: '',
    companyName: '',
    contactPhone: '',
    websiteUrl: '',

    // Module Info
    moduleName: '',
    moduleDescription: '',
    moduleCategory: 'interactive',
    moduleVersion: '1.0.0',
    repositoryUrl: '',

    // Webhook Config
    webhookUrl: '',
    webhookSecret: '',
    webhookPerCommunity: false,

    // Scopes
    scopes: [],
    scopeJustification: '',

    // Pricing
    pricingModel: 'flat-rate',
    pricingAmount: 0,
    pricingCurrency: 'USD',

    // Payment
    paymentMethod: 'paypal',
    paymentDetails: {},

    // Support
    supportedPlatforms: ['twitch', 'discord', 'slack'],
    documentationUrl: '',
    supportEmail: '',
    supportContactUrl: '',
  });

  const [paymentDetails, setPaymentDetails] = useState({
    paypal_email: '',
    stripe_account: '',
    check_payee: '',
    check_address: '',
    bank_account_holder: '',
    bank_account_number: '',
    bank_routing_number: '',
    bank_swift_code: '',
    other_details: '',
  });

  const handleBasicChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleScopeToggle = (scopeId) => {
    setFormData(prev => ({
      ...prev,
      scopes: prev.scopes.includes(scopeId)
        ? prev.scopes.filter(s => s !== scopeId)
        : [...prev.scopes, scopeId],
    }));
  };

  const handlePlatformToggle = (platform) => {
    setFormData(prev => ({
      ...prev,
      supportedPlatforms: prev.supportedPlatforms.includes(platform)
        ? prev.supportedPlatforms.filter(p => p !== platform)
        : [...prev.supportedPlatforms, platform],
    }));
  };

  const handlePaymentDetailsChange = (e) => {
    const { name, value } = e.target;
    setPaymentDetails(prev => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      // Filter payment details based on selected method
      const relevantPaymentDetails = {};
      switch (formData.paymentMethod) {
        case 'paypal':
          relevantPaymentDetails.paypal_email = paymentDetails.paypal_email;
          break;
        case 'stripe':
          relevantPaymentDetails.stripe_account = paymentDetails.stripe_account;
          break;
        case 'check':
          relevantPaymentDetails.check_payee = paymentDetails.check_payee;
          relevantPaymentDetails.check_address = paymentDetails.check_address;
          break;
        case 'bank_transfer':
          relevantPaymentDetails.bank_account_holder = paymentDetails.bank_account_holder;
          relevantPaymentDetails.bank_account_number = paymentDetails.bank_account_number;
          relevantPaymentDetails.bank_routing_number = paymentDetails.bank_routing_number;
          relevantPaymentDetails.bank_swift_code = paymentDetails.bank_swift_code;
          break;
        case 'other':
          relevantPaymentDetails.other_details = paymentDetails.other_details;
          break;
        default:
          break;
      }

      const submitData = {
        ...formData,
        paymentDetails: relevantPaymentDetails,
      };

      const response = await fetch('/api/v1/vendor/submit', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submitData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || 'Submission failed');
      }

      setSuccess(true);
      setSubmissionId(data.submission.submissionId);

      // Scroll to top
      window.scrollTo(0, 0);

      // Reset form after 3 seconds
      setTimeout(() => {
        navigate('/vendor/submission-status', {
          state: { submissionId: data.submission.submissionId }
        });
      }, 3000);
    } catch (err) {
      setError(err.message || 'Failed to submit module');
      window.scrollTo(0, 0);
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="vendor-submission-success">
        <div className="success-message">
          <div className="success-icon">✓</div>
          <h2>Module Submission Received!</h2>
          <p>Thank you for submitting your module to Waddles Marketplace.</p>
          <p className="submission-id">Submission ID: {submissionId}</p>
          <p>We've received your submission and will review it within 5-7 business days.</p>
          <p>You'll receive updates at: <strong>{formData.vendorEmail}</strong></p>
          <button
            onClick={() => navigate('/vendor/submission-status')}
            className="btn btn-primary"
          >
            Check Submission Status
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="vendor-submission-form">
      <div className="form-container">
        <h1>Submit Your Module to Waddles Marketplace</h1>
        <p className="form-subtitle">
          Share your module with the Waddles community. Our admin team will review your submission
          and contact you within 5-7 business days.
        </p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Section 1: Vendor Information */}
          <section className="form-section">
            <h2>1. Vendor Information</h2>

            <div className="form-group">
              <label htmlFor="vendorName">Vendor Name *</label>
              <input
                type="text"
                id="vendorName"
                name="vendorName"
                value={formData.vendorName}
                onChange={handleBasicChange}
                placeholder="Your name or business name"
                required
              />
              <small>How you'll be credited in the marketplace</small>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="vendorEmail">Email Address *</label>
                <input
                  type="email"
                  id="vendorEmail"
                  name="vendorEmail"
                  value={formData.vendorEmail}
                  onChange={handleBasicChange}
                  placeholder="your@email.com"
                  required
                />
                <small>For submission updates and payment communication</small>
              </div>

              <div className="form-group">
                <label htmlFor="contactPhone">Phone (Optional)</label>
                <input
                  type="tel"
                  id="contactPhone"
                  name="contactPhone"
                  value={formData.contactPhone}
                  onChange={handleBasicChange}
                  placeholder="+1 (555) 123-4567"
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="companyName">Company Name (Optional)</label>
                <input
                  type="text"
                  id="companyName"
                  name="companyName"
                  value={formData.companyName}
                  onChange={handleBasicChange}
                  placeholder="Your company name"
                />
              </div>

              <div className="form-group">
                <label htmlFor="websiteUrl">Website (Optional)</label>
                <input
                  type="url"
                  id="websiteUrl"
                  name="websiteUrl"
                  value={formData.websiteUrl}
                  onChange={handleBasicChange}
                  placeholder="https://example.com"
                />
              </div>
            </div>
          </section>

          {/* Section 2: Module Information */}
          <section className="form-section">
            <h2>2. Module Information</h2>

            <div className="form-group">
              <label htmlFor="moduleName">Module Name *</label>
              <input
                type="text"
                id="moduleName"
                name="moduleName"
                value={formData.moduleName}
                onChange={handleBasicChange}
                placeholder="e.g., Weather API Integration"
                required
              />
              <small>Display name in the marketplace</small>
            </div>

            <div className="form-group">
              <label htmlFor="moduleDescription">Module Description *</label>
              <textarea
                id="moduleDescription"
                name="moduleDescription"
                value={formData.moduleDescription}
                onChange={handleBasicChange}
                rows="4"
                placeholder="Describe what your module does, its features, and why users should install it..."
                required
              />
              <small>Max 500 characters</small>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="moduleCategory">Category *</label>
                <select
                  id="moduleCategory"
                  name="moduleCategory"
                  value={formData.moduleCategory}
                  onChange={handleBasicChange}
                  required
                >
                  {MODULE_CATEGORIES.map(cat => (
                    <option key={cat.id} value={cat.id}>{cat.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="moduleVersion">Version *</label>
                <input
                  type="text"
                  id="moduleVersion"
                  name="moduleVersion"
                  value={formData.moduleVersion}
                  onChange={handleBasicChange}
                  placeholder="1.0.0"
                  pattern="^\d+\.\d+\.\d+$"
                  required
                />
                <small>Semantic versioning (e.g., 1.0.0)</small>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="repositoryUrl">Repository URL (Optional)</label>
              <input
                type="url"
                id="repositoryUrl"
                name="repositoryUrl"
                value={formData.repositoryUrl}
                onChange={handleBasicChange}
                placeholder="https://github.com/username/module"
              />
              <small>Link to your GitHub, GitLab, or Gitea repository</small>
            </div>
          </section>

          {/* Section 3: Webhook Configuration */}
          <section className="form-section">
            <h2>3. Webhook Configuration</h2>
            <p className="section-help">
              Waddles will send events to your webhook when users interact with your module.
            </p>

            <div className="form-group">
              <label htmlFor="webhookUrl">Webhook URL *</label>
              <input
                type="url"
                id="webhookUrl"
                name="webhookUrl"
                value={formData.webhookUrl}
                onChange={handleBasicChange}
                placeholder="https://api.example.com/waddlebot/webhook"
                required
              />
              <small>Must be HTTPS. Receives POST requests with module events.</small>
            </div>

            <div className="form-group">
              <label htmlFor="webhookSecret">Webhook Secret (Optional)</label>
              <input
                type="password"
                id="webhookSecret"
                name="webhookSecret"
                value={formData.webhookSecret}
                onChange={handleBasicChange}
                placeholder="Leave empty to auto-generate"
              />
              <small>Used to sign webhook requests for security verification</small>
            </div>

            <div className="form-group checkbox">
              <input
                type="checkbox"
                id="webhookPerCommunity"
                name="webhookPerCommunity"
                checked={formData.webhookPerCommunity}
                onChange={handleBasicChange}
              />
              <label htmlFor="webhookPerCommunity">
                Different webhook URL per community
              </label>
              <small>
                If checked, each community using your module gets its own webhook URL.
                If unchecked, you receive all events through a single webhook.
              </small>
            </div>
          </section>

          {/* Section 4: Permissions/Scopes */}
          <section className="form-section">
            <h2>4. Required Permissions</h2>
            <p className="section-help">
              Select the permissions your module needs. Communities will see what data you're accessing.
            </p>

            <div className="scopes-container">
              {SCOPES.map(scope => (
                <div key={scope.id} className={`scope-checkbox risk-${scope.risk}`}>
                  <input
                    type="checkbox"
                    id={scope.id}
                    checked={formData.scopes.includes(scope.id)}
                    onChange={() => handleScopeToggle(scope.id)}
                  />
                  <label htmlFor={scope.id}>
                    <span className="scope-name">{scope.name}</span>
                    <span className={`scope-risk risk-${scope.risk}`}>{scope.risk}</span>
                  </label>
                </div>
              ))}
            </div>

            <div className="form-group">
              <label htmlFor="scopeJustification">Why do you need these permissions? *</label>
              <textarea
                id="scopeJustification"
                name="scopeJustification"
                value={formData.scopeJustification}
                onChange={handleBasicChange}
                rows="3"
                placeholder="Explain how your module uses each permission..."
                required
              />
            </div>
          </section>

          {/* Section 5: Pricing */}
          <section className="form-section">
            <h2>5. Pricing Model</h2>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="pricingModel">Pricing Type *</label>
                <select
                  id="pricingModel"
                  name="pricingModel"
                  value={formData.pricingModel}
                  onChange={handleBasicChange}
                  required
                >
                  <option value="flat-rate">Flat Rate (one-time or monthly)</option>
                  <option value="per-seat">Per Seat (price per user/channel)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="pricingAmount">Price in USD *</label>
                <div className="input-group">
                  <span className="currency">$</span>
                  <input
                    type="number"
                    id="pricingAmount"
                    name="pricingAmount"
                    value={formData.pricingAmount}
                    onChange={handleBasicChange}
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                    required
                  />
                </div>
                <small>Set to $0 for free modules. Leave blank if not yet decided.</small>
              </div>
            </div>
          </section>

          {/* Section 6: Payment Information */}
          <section className="form-section">
            <h2>6. Payment Information</h2>
            <p className="section-help">
              Where should payments be sent? We handle billing & invoicing through our payment processor.
            </p>

            <div className="form-group">
              <label>Preferred Payment Method *</label>
              <div className="payment-methods">
                {PAYMENT_METHODS.map(method => (
                  <div key={method.id} className="payment-option">
                    <input
                      type="radio"
                      id={`payment-${method.id}`}
                      name="paymentMethod"
                      value={method.id}
                      checked={formData.paymentMethod === method.id}
                      onChange={handleBasicChange}
                    />
                    <label htmlFor={`payment-${method.id}`}>{method.name}</label>
                  </div>
                ))}
              </div>
            </div>

            {/* PayPal Details */}
            {formData.paymentMethod === 'paypal' && (
              <div className="form-group">
                <label htmlFor="paypal_email">PayPal Email Address *</label>
                <input
                  type="email"
                  name="paypal_email"
                  value={paymentDetails.paypal_email}
                  onChange={handlePaymentDetailsChange}
                  placeholder="your@paypal.com"
                />
              </div>
            )}

            {/* Stripe Details */}
            {formData.paymentMethod === 'stripe' && (
              <div className="form-group">
                <label htmlFor="stripe_account">Stripe Account Email/ID *</label>
                <input
                  type="text"
                  name="stripe_account"
                  value={paymentDetails.stripe_account}
                  onChange={handlePaymentDetailsChange}
                  placeholder="your-stripe-account@example.com"
                />
              </div>
            )}

            {/* Check Payment Details */}
            {formData.paymentMethod === 'check' && (
              <>
                <div className="form-group">
                  <label htmlFor="check_payee">Make Checks Payable To *</label>
                  <input
                    type="text"
                    name="check_payee"
                    value={paymentDetails.check_payee}
                    onChange={handlePaymentDetailsChange}
                    placeholder="Business Name"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="check_address">Mailing Address *</label>
                  <textarea
                    name="check_address"
                    value={paymentDetails.check_address}
                    onChange={handlePaymentDetailsChange}
                    rows="3"
                    placeholder="Full mailing address for checks"
                  />
                </div>
              </>
            )}

            {/* Bank Transfer Details */}
            {formData.paymentMethod === 'bank_transfer' && (
              <>
                <div className="form-group">
                  <label htmlFor="bank_account_holder">Account Holder Name *</label>
                  <input
                    type="text"
                    name="bank_account_holder"
                    value={paymentDetails.bank_account_holder}
                    onChange={handlePaymentDetailsChange}
                    placeholder="Full name"
                  />
                </div>
                <div className="form-row">
                  <div className="form-group">
                    <label htmlFor="bank_account_number">Account Number *</label>
                    <input
                      type="password"
                      name="bank_account_number"
                      value={paymentDetails.bank_account_number}
                      onChange={handlePaymentDetailsChange}
                      placeholder="Account number"
                    />
                  </div>
                  <div className="form-group">
                    <label htmlFor="bank_routing_number">Routing Number *</label>
                    <input
                      type="password"
                      name="bank_routing_number"
                      value={paymentDetails.bank_routing_number}
                      onChange={handlePaymentDetailsChange}
                      placeholder="Routing number"
                    />
                  </div>
                </div>
                <div className="form-group">
                  <label htmlFor="bank_swift_code">SWIFT Code (International)</label>
                  <input
                    type="text"
                    name="bank_swift_code"
                    value={paymentDetails.bank_swift_code}
                    onChange={handlePaymentDetailsChange}
                    placeholder="SWIFT code for international transfers"
                  />
                </div>
              </>
            )}

            {/* Other Payment Method */}
            {formData.paymentMethod === 'other' && (
              <div className="form-group">
                <label htmlFor="other_details">Payment Details *</label>
                <textarea
                  name="other_details"
                  value={paymentDetails.other_details}
                  onChange={handlePaymentDetailsChange}
                  rows="3"
                  placeholder="Describe your preferred payment method..."
                />
              </div>
            )}

            <div className="payment-disclaimer">
              <strong>⚠ Important Note about Processing Fees:</strong>
              <p>
                Payment processors (PayPal, Stripe, etc.) charge standard transaction fees (typically 2.2-3% + $0.30).
                These fees are <strong>deducted from your payment by the processor</strong>, not by Waddles.
                You'll see the net amount after fees in your payment summary.
              </p>
            </div>
          </section>

          {/* Section 7: Supported Platforms */}
          <section className="form-section">
            <h2>7. Supported Platforms</h2>

            <div className="platforms-container">
              {['twitch', 'discord', 'slack'].map(platform => (
                <div key={platform} className="platform-checkbox">
                  <input
                    type="checkbox"
                    id={`platform-${platform}`}
                    checked={formData.supportedPlatforms.includes(platform)}
                    onChange={() => handlePlatformToggle(platform)}
                  />
                  <label htmlFor={`platform-${platform}`}>
                    {platform.charAt(0).toUpperCase() + platform.slice(1)}
                  </label>
                </div>
              ))}
            </div>
          </section>

          {/* Section 8: Support Information */}
          <section className="form-section">
            <h2>8. Support & Documentation</h2>

            <div className="form-group">
              <label htmlFor="documentationUrl">Documentation URL (Optional)</label>
              <input
                type="url"
                id="documentationUrl"
                name="documentationUrl"
                value={formData.documentationUrl}
                onChange={handleBasicChange}
                placeholder="https://docs.example.com"
              />
              <small>Link to your module's user documentation</small>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label htmlFor="supportEmail">Support Email (Optional)</label>
                <input
                  type="email"
                  id="supportEmail"
                  name="supportEmail"
                  value={formData.supportEmail}
                  onChange={handleBasicChange}
                  placeholder="support@example.com"
                />
              </div>

              <div className="form-group">
                <label htmlFor="supportContactUrl">Support Portal URL (Optional)</label>
                <input
                  type="url"
                  id="supportContactUrl"
                  name="supportContactUrl"
                  value={formData.supportContactUrl}
                  onChange={handleBasicChange}
                  placeholder="https://support.example.com"
                />
              </div>
            </div>
          </section>

          {/* Submit Button */}
          <div className="form-actions">
            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-large"
            >
              {loading ? 'Submitting...' : 'Submit for Review'}
            </button>
            <p className="form-help">
              By submitting, you agree to our vendor agreement and terms of service.
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}
