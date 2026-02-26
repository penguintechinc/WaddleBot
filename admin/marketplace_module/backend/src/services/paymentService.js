import stripeService from './stripeService.js';
import paypalService from './paypalService.js';

/**
 * Unified Payment Service
 * Provides a unified interface for payment operations across multiple providers
 * Supports Stripe and PayPal payment providers
 */
class PaymentService {
  constructor() {
    this.providers = {
      stripe: stripeService,
      paypal: paypalService,
    };
    this.defaultProvider = process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe';
  }

  /**
   * Get payment provider instance
   * @param {string} provider - Provider name (stripe or paypal)
   * @returns {Object} Provider service instance
   */
  getProvider(provider = this.defaultProvider) {
    const providerService = this.providers[provider.toLowerCase()];
    if (!providerService) {
      throw new Error(`Unsupported payment provider: ${provider}`);
    }
    return providerService;
  }

  /**
   * Create a checkout session/order for one-time payment
   * @param {Object} options - Payment options
   * @param {string} options.provider - Payment provider (stripe or paypal)
   * @param {Array} options.items - Line items
   * @param {string} options.customerEmail - Customer email
   * @param {string} options.successUrl - Success redirect URL
   * @param {string} options.cancelUrl - Cancel redirect URL
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Checkout session/order
   */
  async createCheckout({
    provider = this.defaultProvider,
    items,
    customerEmail,
    successUrl,
    cancelUrl,
    metadata = {},
  }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.createCheckoutSession({
          items,
          customerEmail,
          successUrl,
          cancelUrl,
          metadata,
        });
      } else if (provider === 'paypal') {
        const totalAmount = items.reduce((sum, item) => {
          return sum + (item.price * (item.quantity || 1));
        }, 0);

        return await providerService.createOrder({
          items,
          totalAmount,
          currency: items[0]?.currency || 'USD',
          returnUrl: successUrl,
          cancelUrl,
          metadata,
        });
      }

      throw new Error(`Checkout creation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service checkout creation error:', error);
      throw error;
    }
  }

  /**
   * Complete/capture a payment
   * @param {string} provider - Payment provider
   * @param {string} id - Session/Order ID
   * @returns {Promise<Object>} Completion result
   */
  async completePayment(provider, id) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        // Stripe payments are automatically captured after checkout session completion
        return await providerService.getCheckoutSession(id);
      } else if (provider === 'paypal') {
        return await providerService.captureOrder(id);
      }

      throw new Error(`Payment completion not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service completion error:', error);
      throw error;
    }
  }

  /**
   * Get payment details
   * @param {string} provider - Payment provider
   * @param {string} id - Payment ID
   * @returns {Promise<Object>} Payment details
   */
  async getPayment(provider, id) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.getCheckoutSession(id);
      } else if (provider === 'paypal') {
        return await providerService.getOrder(id);
      }

      throw new Error(`Get payment not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service get payment error:', error);
      throw error;
    }
  }

  /**
   * Create a subscription
   * @param {Object} options - Subscription options
   * @param {string} options.provider - Payment provider
   * @param {string} options.planId - Plan/Price ID
   * @param {string} options.customerEmail - Customer email
   * @param {string} options.successUrl - Success redirect URL
   * @param {string} options.cancelUrl - Cancel redirect URL
   * @param {number} options.trialPeriodDays - Trial period in days
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Subscription session/object
   */
  async createSubscription({
    provider = this.defaultProvider,
    planId,
    customerEmail,
    successUrl,
    cancelUrl,
    trialPeriodDays = 0,
    metadata = {},
  }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.createSubscriptionSession({
          priceId: planId,
          customerEmail,
          successUrl,
          cancelUrl,
          trialPeriodDays,
          metadata,
        });
      } else if (provider === 'paypal') {
        return await providerService.createSubscription({
          planId,
          returnUrl: successUrl,
          cancelUrl,
          subscriber: { email_address: customerEmail },
        });
      }

      throw new Error(`Subscription creation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service subscription creation error:', error);
      throw error;
    }
  }

  /**
   * Get subscription details
   * @param {string} provider - Payment provider
   * @param {string} subscriptionId - Subscription ID
   * @returns {Promise<Object>} Subscription details
   */
  async getSubscription(provider, subscriptionId) {
    try {
      const providerService = this.getProvider(provider);
      return await providerService.getSubscription(subscriptionId);
    } catch (error) {
      console.error('Payment service get subscription error:', error);
      throw error;
    }
  }

  /**
   * Update a subscription
   * @param {string} provider - Payment provider
   * @param {string} subscriptionId - Subscription ID
   * @param {Object} updates - Updates to apply
   * @returns {Promise<Object>} Updated subscription
   */
  async updateSubscription(provider, subscriptionId, updates) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.updateSubscription(subscriptionId, updates);
      }

      throw new Error(`Subscription update not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service subscription update error:', error);
      throw error;
    }
  }

  /**
   * Cancel a subscription
   * @param {string} provider - Payment provider
   * @param {string} subscriptionId - Subscription ID
   * @param {boolean} immediately - Cancel immediately or at period end
   * @param {string} reason - Cancellation reason
   * @returns {Promise<Object>} Cancellation result
   */
  async cancelSubscription(provider, subscriptionId, immediately = false, reason = '') {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.cancelSubscription(subscriptionId, immediately);
      } else if (provider === 'paypal') {
        return await providerService.cancelSubscription(subscriptionId, reason);
      }

      throw new Error(`Subscription cancellation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service subscription cancellation error:', error);
      throw error;
    }
  }

  /**
   * Reactivate a cancelled subscription
   * @param {string} provider - Payment provider
   * @param {string} subscriptionId - Subscription ID
   * @returns {Promise<Object>} Reactivation result
   */
  async reactivateSubscription(provider, subscriptionId) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.reactivateSubscription(subscriptionId);
      }

      throw new Error(`Subscription reactivation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service subscription reactivation error:', error);
      throw error;
    }
  }

  /**
   * Create a refund
   * @param {Object} options - Refund options
   * @param {string} options.provider - Payment provider
   * @param {string} options.paymentId - Payment/Capture ID
   * @param {number} options.amount - Amount to refund (optional for full refund)
   * @param {string} options.currency - Currency code
   * @param {string} options.reason - Refund reason
   * @param {string} options.note - Note for customer
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Refund object
   */
  async createRefund({
    provider,
    paymentId,
    amount,
    currency = 'USD',
    reason = 'requested_by_customer',
    note = '',
    metadata = {},
  }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.createRefund({
          paymentIntentId: paymentId,
          amount,
          reason,
          metadata,
        });
      } else if (provider === 'paypal') {
        return await providerService.createRefund(paymentId, {
          amount,
          currency,
          note,
        });
      }

      throw new Error(`Refund creation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service refund creation error:', error);
      throw error;
    }
  }

  /**
   * Get refund details
   * @param {string} provider - Payment provider
   * @param {string} refundId - Refund ID
   * @returns {Promise<Object>} Refund details
   */
  async getRefund(provider, refundId) {
    try {
      const providerService = this.getProvider(provider);
      return await providerService.getRefund(refundId);
    } catch (error) {
      console.error('Payment service get refund error:', error);
      throw error;
    }
  }

  /**
   * Handle webhook from payment provider
   * @param {Object} options - Webhook options
   * @param {string} options.provider - Payment provider
   * @param {Object} options.headers - Request headers
   * @param {string|Object} options.payload - Request payload
   * @returns {Promise<Object>} Webhook processing result
   */
  async handleWebhook({ provider, headers, payload }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        const signature = headers['stripe-signature'];
        const event = providerService.constructWebhookEvent(payload, signature);
        return await providerService.handleWebhook(event);
      } else if (provider === 'paypal') {
        const isValid = await providerService.verifyWebhookSignature(headers, payload);
        if (!isValid) {
          throw new Error('Invalid webhook signature');
        }
        return await providerService.handleWebhook(payload);
      }

      throw new Error(`Webhook handling not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service webhook handling error:', error);
      throw error;
    }
  }

  /**
   * Create a customer
   * @param {Object} options - Customer options
   * @param {string} options.provider - Payment provider
   * @param {string} options.email - Customer email
   * @param {string} options.name - Customer name
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Customer object
   */
  async createCustomer({ provider = this.defaultProvider, email, name, metadata = {} }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.createCustomer({ email, name, metadata });
      }

      throw new Error(`Customer creation not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service customer creation error:', error);
      throw error;
    }
  }

  /**
   * Get customer details
   * @param {string} provider - Payment provider
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Customer details
   */
  async getCustomer(provider, customerId) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.getCustomer(customerId);
      }

      throw new Error(`Get customer not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service get customer error:', error);
      throw error;
    }
  }

  /**
   * List payment methods for a customer
   * @param {string} provider - Payment provider
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} List of payment methods
   */
  async listPaymentMethods(provider, customerId) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        return await providerService.listPaymentMethods(customerId);
      }

      throw new Error(`List payment methods not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service list payment methods error:', error);
      throw error;
    }
  }

  /**
   * Validate payment provider configuration
   * @param {string} provider - Payment provider to validate
   * @returns {Object} Validation result
   */
  validateProviderConfig(provider = this.defaultProvider) {
    const errors = [];

    if (provider === 'stripe') {
      if (!process.env.STRIPE_SECRET_KEY) {
        errors.push('STRIPE_SECRET_KEY is not configured');
      }
      if (!process.env.STRIPE_WEBHOOK_SECRET) {
        errors.push('STRIPE_WEBHOOK_SECRET is not configured');
      }
    } else if (provider === 'paypal') {
      if (!process.env.PAYPAL_CLIENT_ID) {
        errors.push('PAYPAL_CLIENT_ID is not configured');
      }
      if (!process.env.PAYPAL_CLIENT_SECRET) {
        errors.push('PAYPAL_CLIENT_SECRET is not configured');
      }
      if (!process.env.PAYPAL_WEBHOOK_ID) {
        errors.push('PAYPAL_WEBHOOK_ID is not configured (recommended for webhook verification)');
      }
    } else {
      errors.push(`Unsupported payment provider: ${provider}`);
    }

    return {
      valid: errors.length === 0,
      errors,
      provider,
    };
  }

  /**
   * Get supported payment providers
   * @returns {Array<string>} List of supported providers
   */
  getSupportedProviders() {
    return Object.keys(this.providers);
  }

  /**
   * Get provider-specific pricing format
   * @param {string} provider - Payment provider
   * @param {number} amount - Amount in base currency units
   * @returns {number} Formatted amount for provider
   */
  formatAmount(provider, amount) {
    if (provider === 'stripe') {
      return Math.round(amount * 100); // Convert to cents
    } else if (provider === 'paypal') {
      return parseFloat(amount.toFixed(2)); // Keep as decimal
    }
    return amount;
  }

  /**
   * Parse provider-specific amount to base currency
   * @param {string} provider - Payment provider
   * @param {number} amount - Provider-specific amount
   * @returns {number} Amount in base currency units
   */
  parseAmount(provider, amount) {
    if (provider === 'stripe') {
      return amount / 100; // Convert from cents
    } else if (provider === 'paypal') {
      return parseFloat(amount); // Already in base units
    }
    return amount;
  }

  /**
   * Create a payment link (for products without custom checkout)
   * @param {Object} options - Payment link options
   * @param {string} options.provider - Payment provider
   * @param {string} options.productId - Product ID
   * @param {number} options.quantity - Quantity
   * @returns {Promise<Object>} Payment link object
   */
  async createPaymentLink({ provider = this.defaultProvider, productId, quantity = 1 }) {
    try {
      const providerService = this.getProvider(provider);

      if (provider === 'stripe') {
        // Stripe payment links - requires REST API
        throw new Error('Stripe payment links require additional implementation');
      }

      throw new Error(`Payment links not implemented for provider: ${provider}`);
    } catch (error) {
      console.error('Payment service payment link creation error:', error);
      throw error;
    }
  }

  /**
   * Get transaction history for a customer
   * @param {string} provider - Payment provider
   * @param {string} customerId - Customer ID
   * @param {Object} options - Query options
   * @returns {Promise<Object>} Transaction history
   */
  async getTransactionHistory(provider, customerId, options = {}) {
    try {
      const providerService = this.getProvider(provider);

      // This would need to be implemented per provider
      throw new Error('Transaction history not yet implemented');
    } catch (error) {
      console.error('Payment service transaction history error:', error);
      throw error;
    }
  }

  /**
   * Generate payment report
   * @param {Object} options - Report options
   * @param {string} options.provider - Payment provider
   * @param {Date} options.startDate - Start date
   * @param {Date} options.endDate - End date
   * @returns {Promise<Object>} Payment report
   */
  async generateReport({ provider, startDate, endDate }) {
    try {
      // This would aggregate payment data for reporting
      throw new Error('Payment reports not yet implemented');
    } catch (error) {
      console.error('Payment service report generation error:', error);
      throw error;
    }
  }
}

export default new PaymentService();
