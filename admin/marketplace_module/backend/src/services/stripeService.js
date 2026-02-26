import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY);

/**
 * Stripe Payment Service
 * Handles all Stripe payment operations including checkout, webhooks, subscriptions, and refunds
 */
class StripeService {
  constructor() {
    this.stripe = stripe;
    this.webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
  }

  /**
   * Create a checkout session for one-time payment
   * @param {Object} options - Checkout session options
   * @param {Array} options.items - Line items for the checkout
   * @param {string} options.customerEmail - Customer email
   * @param {string} options.successUrl - URL to redirect on success
   * @param {string} options.cancelUrl - URL to redirect on cancel
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Checkout session object
   */
  async createCheckoutSession({ items, customerEmail, successUrl, cancelUrl, metadata = {} }) {
    try {
      const lineItems = items.map(item => ({
        price_data: {
          currency: item.currency || 'usd',
          product_data: {
            name: item.name,
            description: item.description,
            images: item.images || [],
          },
          unit_amount: Math.round(item.price * 100), // Convert to cents
        },
        quantity: item.quantity || 1,
      }));

      const session = await this.stripe.checkout.sessions.create({
        payment_method_types: ['card'],
        line_items: lineItems,
        mode: 'payment',
        customer_email: customerEmail,
        success_url: successUrl,
        cancel_url: cancelUrl,
        metadata: {
          ...metadata,
          source: 'waddlebot_marketplace',
        },
        payment_intent_data: {
          metadata: {
            ...metadata,
          },
        },
      });

      return {
        success: true,
        sessionId: session.id,
        url: session.url,
        session,
      };
    } catch (error) {
      console.error('Stripe checkout session creation error:', error);
      throw new Error(`Failed to create checkout session: ${error.message}`);
    }
  }

  /**
   * Create a subscription checkout session
   * @param {Object} options - Subscription options
   * @param {string} options.priceId - Stripe price ID
   * @param {string} options.customerEmail - Customer email
   * @param {string} options.successUrl - URL to redirect on success
   * @param {string} options.cancelUrl - URL to redirect on cancel
   * @param {number} options.trialPeriodDays - Trial period in days
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Checkout session object
   */
  async createSubscriptionSession({
    priceId,
    customerEmail,
    successUrl,
    cancelUrl,
    trialPeriodDays = 0,
    metadata = {},
  }) {
    try {
      const sessionConfig = {
        payment_method_types: ['card'],
        line_items: [
          {
            price: priceId,
            quantity: 1,
          },
        ],
        mode: 'subscription',
        customer_email: customerEmail,
        success_url: successUrl,
        cancel_url: cancelUrl,
        metadata: {
          ...metadata,
          source: 'waddlebot_marketplace',
        },
        subscription_data: {
          metadata: {
            ...metadata,
          },
        },
      };

      if (trialPeriodDays > 0) {
        sessionConfig.subscription_data.trial_period_days = trialPeriodDays;
      }

      const session = await this.stripe.checkout.sessions.create(sessionConfig);

      return {
        success: true,
        sessionId: session.id,
        url: session.url,
        session,
      };
    } catch (error) {
      console.error('Stripe subscription session creation error:', error);
      throw new Error(`Failed to create subscription session: ${error.message}`);
    }
  }

  /**
   * Retrieve a checkout session
   * @param {string} sessionId - Checkout session ID
   * @returns {Promise<Object>} Session details
   */
  async getCheckoutSession(sessionId) {
    try {
      const session = await this.stripe.checkout.sessions.retrieve(sessionId);
      return {
        success: true,
        session,
      };
    } catch (error) {
      console.error('Stripe get session error:', error);
      throw new Error(`Failed to retrieve session: ${error.message}`);
    }
  }

  /**
   * Create a payment intent for custom checkout flows
   * @param {Object} options - Payment intent options
   * @param {number} options.amount - Amount in currency units (e.g., dollars)
   * @param {string} options.currency - Currency code
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Payment intent object
   */
  async createPaymentIntent({ amount, currency = 'usd', metadata = {} }) {
    try {
      const paymentIntent = await this.stripe.paymentIntents.create({
        amount: Math.round(amount * 100), // Convert to cents
        currency,
        metadata: {
          ...metadata,
          source: 'waddlebot_marketplace',
        },
      });

      return {
        success: true,
        clientSecret: paymentIntent.client_secret,
        paymentIntent,
      };
    } catch (error) {
      console.error('Stripe payment intent creation error:', error);
      throw new Error(`Failed to create payment intent: ${error.message}`);
    }
  }

  /**
   * Verify webhook signature and construct event
   * @param {string} payload - Raw request body
   * @param {string} signature - Stripe signature header
   * @returns {Object} Verified event object
   */
  constructWebhookEvent(payload, signature) {
    try {
      const event = this.stripe.webhooks.constructEvent(
        payload,
        signature,
        this.webhookSecret
      );
      return event;
    } catch (error) {
      console.error('Webhook signature verification failed:', error);
      throw new Error(`Webhook verification failed: ${error.message}`);
    }
  }

  /**
   * Handle webhook events
   * @param {Object} event - Stripe event object
   * @returns {Promise<Object>} Processing result
   */
  async handleWebhook(event) {
    try {
      let result = { processed: false };

      switch (event.type) {
        case 'checkout.session.completed':
          result = await this.handleCheckoutCompleted(event.data.object);
          break;

        case 'payment_intent.succeeded':
          result = await this.handlePaymentSucceeded(event.data.object);
          break;

        case 'payment_intent.payment_failed':
          result = await this.handlePaymentFailed(event.data.object);
          break;

        case 'customer.subscription.created':
          result = await this.handleSubscriptionCreated(event.data.object);
          break;

        case 'customer.subscription.updated':
          result = await this.handleSubscriptionUpdated(event.data.object);
          break;

        case 'customer.subscription.deleted':
          result = await this.handleSubscriptionDeleted(event.data.object);
          break;

        case 'invoice.payment_succeeded':
          result = await this.handleInvoicePaymentSucceeded(event.data.object);
          break;

        case 'invoice.payment_failed':
          result = await this.handleInvoicePaymentFailed(event.data.object);
          break;

        default:
          console.log(`Unhandled event type: ${event.type}`);
          result = { processed: false, message: 'Event type not handled' };
      }

      return {
        success: true,
        eventType: event.type,
        ...result,
      };
    } catch (error) {
      console.error('Webhook handling error:', error);
      throw error;
    }
  }

  /**
   * Handle completed checkout session
   * @param {Object} session - Checkout session object
   * @returns {Promise<Object>} Processing result
   */
  async handleCheckoutCompleted(session) {
    console.log('Checkout session completed:', session.id);

    // Extract relevant information
    const result = {
      processed: true,
      sessionId: session.id,
      customerId: session.customer,
      customerEmail: session.customer_email,
      paymentStatus: session.payment_status,
      amountTotal: session.amount_total / 100, // Convert from cents
      currency: session.currency,
      metadata: session.metadata,
      mode: session.mode,
    };

    // If this is a subscription, get subscription details
    if (session.mode === 'subscription' && session.subscription) {
      result.subscriptionId = session.subscription;
    }

    // If this is a payment, get payment intent details
    if (session.mode === 'payment' && session.payment_intent) {
      result.paymentIntentId = session.payment_intent;
    }

    // TODO: Store in database, send confirmation email, fulfill order
    // This is where you'd integrate with your order management system

    return result;
  }

  /**
   * Handle successful payment intent
   * @param {Object} paymentIntent - Payment intent object
   * @returns {Promise<Object>} Processing result
   */
  async handlePaymentSucceeded(paymentIntent) {
    console.log('Payment succeeded:', paymentIntent.id);

    return {
      processed: true,
      paymentIntentId: paymentIntent.id,
      amount: paymentIntent.amount / 100,
      currency: paymentIntent.currency,
      metadata: paymentIntent.metadata,
    };
  }

  /**
   * Handle failed payment intent
   * @param {Object} paymentIntent - Payment intent object
   * @returns {Promise<Object>} Processing result
   */
  async handlePaymentFailed(paymentIntent) {
    console.log('Payment failed:', paymentIntent.id);

    return {
      processed: true,
      paymentIntentId: paymentIntent.id,
      failureMessage: paymentIntent.last_payment_error?.message,
      metadata: paymentIntent.metadata,
    };
  }

  /**
   * Handle subscription created
   * @param {Object} subscription - Subscription object
   * @returns {Promise<Object>} Processing result
   */
  async handleSubscriptionCreated(subscription) {
    console.log('Subscription created:', subscription.id);

    return {
      processed: true,
      subscriptionId: subscription.id,
      customerId: subscription.customer,
      status: subscription.status,
      currentPeriodEnd: subscription.current_period_end,
      metadata: subscription.metadata,
    };
  }

  /**
   * Handle subscription updated
   * @param {Object} subscription - Subscription object
   * @returns {Promise<Object>} Processing result
   */
  async handleSubscriptionUpdated(subscription) {
    console.log('Subscription updated:', subscription.id);

    return {
      processed: true,
      subscriptionId: subscription.id,
      status: subscription.status,
      currentPeriodEnd: subscription.current_period_end,
      cancelAtPeriodEnd: subscription.cancel_at_period_end,
    };
  }

  /**
   * Handle subscription deleted/cancelled
   * @param {Object} subscription - Subscription object
   * @returns {Promise<Object>} Processing result
   */
  async handleSubscriptionDeleted(subscription) {
    console.log('Subscription deleted:', subscription.id);

    return {
      processed: true,
      subscriptionId: subscription.id,
      status: subscription.status,
      canceledAt: subscription.canceled_at,
    };
  }

  /**
   * Handle successful invoice payment (for subscriptions)
   * @param {Object} invoice - Invoice object
   * @returns {Promise<Object>} Processing result
   */
  async handleInvoicePaymentSucceeded(invoice) {
    console.log('Invoice payment succeeded:', invoice.id);

    return {
      processed: true,
      invoiceId: invoice.id,
      subscriptionId: invoice.subscription,
      amountPaid: invoice.amount_paid / 100,
      currency: invoice.currency,
    };
  }

  /**
   * Handle failed invoice payment
   * @param {Object} invoice - Invoice object
   * @returns {Promise<Object>} Processing result
   */
  async handleInvoicePaymentFailed(invoice) {
    console.log('Invoice payment failed:', invoice.id);

    return {
      processed: true,
      invoiceId: invoice.id,
      subscriptionId: invoice.subscription,
      attemptCount: invoice.attempt_count,
    };
  }

  /**
   * Create a refund for a payment
   * @param {Object} options - Refund options
   * @param {string} options.paymentIntentId - Payment intent ID
   * @param {number} options.amount - Amount to refund (optional, full refund if not specified)
   * @param {string} options.reason - Reason for refund
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Refund object
   */
  async createRefund({ paymentIntentId, amount, reason = 'requested_by_customer', metadata = {} }) {
    try {
      const refundData = {
        payment_intent: paymentIntentId,
        reason,
        metadata: {
          ...metadata,
          source: 'waddlebot_marketplace',
        },
      };

      if (amount) {
        refundData.amount = Math.round(amount * 100); // Convert to cents
      }

      const refund = await this.stripe.refunds.create(refundData);

      return {
        success: true,
        refundId: refund.id,
        amount: refund.amount / 100,
        status: refund.status,
        refund,
      };
    } catch (error) {
      console.error('Stripe refund creation error:', error);
      throw new Error(`Failed to create refund: ${error.message}`);
    }
  }

  /**
   * Get refund details
   * @param {string} refundId - Refund ID
   * @returns {Promise<Object>} Refund details
   */
  async getRefund(refundId) {
    try {
      const refund = await this.stripe.refunds.retrieve(refundId);
      return {
        success: true,
        refund,
      };
    } catch (error) {
      console.error('Stripe get refund error:', error);
      throw new Error(`Failed to retrieve refund: ${error.message}`);
    }
  }

  /**
   * Cancel a subscription
   * @param {string} subscriptionId - Subscription ID
   * @param {boolean} immediately - Cancel immediately or at period end
   * @returns {Promise<Object>} Updated subscription
   */
  async cancelSubscription(subscriptionId, immediately = false) {
    try {
      let subscription;

      if (immediately) {
        subscription = await this.stripe.subscriptions.cancel(subscriptionId);
      } else {
        subscription = await this.stripe.subscriptions.update(subscriptionId, {
          cancel_at_period_end: true,
        });
      }

      return {
        success: true,
        subscriptionId: subscription.id,
        status: subscription.status,
        cancelAtPeriodEnd: subscription.cancel_at_period_end,
        currentPeriodEnd: subscription.current_period_end,
        subscription,
      };
    } catch (error) {
      console.error('Stripe subscription cancellation error:', error);
      throw new Error(`Failed to cancel subscription: ${error.message}`);
    }
  }

  /**
   * Reactivate a cancelled subscription
   * @param {string} subscriptionId - Subscription ID
   * @returns {Promise<Object>} Updated subscription
   */
  async reactivateSubscription(subscriptionId) {
    try {
      const subscription = await this.stripe.subscriptions.update(subscriptionId, {
        cancel_at_period_end: false,
      });

      return {
        success: true,
        subscriptionId: subscription.id,
        status: subscription.status,
        subscription,
      };
    } catch (error) {
      console.error('Stripe subscription reactivation error:', error);
      throw new Error(`Failed to reactivate subscription: ${error.message}`);
    }
  }

  /**
   * Get subscription details
   * @param {string} subscriptionId - Subscription ID
   * @returns {Promise<Object>} Subscription details
   */
  async getSubscription(subscriptionId) {
    try {
      const subscription = await this.stripe.subscriptions.retrieve(subscriptionId);
      return {
        success: true,
        subscription,
      };
    } catch (error) {
      console.error('Stripe get subscription error:', error);
      throw new Error(`Failed to retrieve subscription: ${error.message}`);
    }
  }

  /**
   * Update subscription
   * @param {string} subscriptionId - Subscription ID
   * @param {Object} updates - Updates to apply
   * @returns {Promise<Object>} Updated subscription
   */
  async updateSubscription(subscriptionId, updates) {
    try {
      const subscription = await this.stripe.subscriptions.update(subscriptionId, updates);
      return {
        success: true,
        subscription,
      };
    } catch (error) {
      console.error('Stripe subscription update error:', error);
      throw new Error(`Failed to update subscription: ${error.message}`);
    }
  }

  /**
   * Create a customer
   * @param {Object} options - Customer options
   * @param {string} options.email - Customer email
   * @param {string} options.name - Customer name
   * @param {Object} options.metadata - Additional metadata
   * @returns {Promise<Object>} Customer object
   */
  async createCustomer({ email, name, metadata = {} }) {
    try {
      const customer = await this.stripe.customers.create({
        email,
        name,
        metadata: {
          ...metadata,
          source: 'waddlebot_marketplace',
        },
      });

      return {
        success: true,
        customerId: customer.id,
        customer,
      };
    } catch (error) {
      console.error('Stripe customer creation error:', error);
      throw new Error(`Failed to create customer: ${error.message}`);
    }
  }

  /**
   * Get customer details
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} Customer details
   */
  async getCustomer(customerId) {
    try {
      const customer = await this.stripe.customers.retrieve(customerId);
      return {
        success: true,
        customer,
      };
    } catch (error) {
      console.error('Stripe get customer error:', error);
      throw new Error(`Failed to retrieve customer: ${error.message}`);
    }
  }

  /**
   * List all payment methods for a customer
   * @param {string} customerId - Customer ID
   * @returns {Promise<Object>} List of payment methods
   */
  async listPaymentMethods(customerId) {
    try {
      const paymentMethods = await this.stripe.paymentMethods.list({
        customer: customerId,
        type: 'card',
      });

      return {
        success: true,
        paymentMethods: paymentMethods.data,
      };
    } catch (error) {
      console.error('Stripe list payment methods error:', error);
      throw new Error(`Failed to list payment methods: ${error.message}`);
    }
  }
}

export default new StripeService();
