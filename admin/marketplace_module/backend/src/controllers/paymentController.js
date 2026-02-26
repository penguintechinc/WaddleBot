import paymentService from '../services/paymentService.js';

/**
 * Payment Controller
 * Handles HTTP requests for payment operations
 */
class PaymentController {
  /**
   * Create a checkout session
   * POST /api/payments/checkout
   */
  async createCheckout(req, res) {
    try {
      const {
        provider = process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe',
        items,
        customerEmail,
        metadata = {},
      } = req.body;

      // Validate required fields
      if (!items || !Array.isArray(items) || items.length === 0) {
        return res.status(400).json({
          success: false,
          error: 'Items array is required',
        });
      }

      if (!customerEmail) {
        return res.status(400).json({
          success: false,
          error: 'Customer email is required',
        });
      }

      // Build URLs
      const baseUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
      const successUrl = `${baseUrl}/checkout/success?session_id={CHECKOUT_SESSION_ID}`;
      const cancelUrl = `${baseUrl}/checkout/cancel`;

      // Create checkout
      const result = await paymentService.createCheckout({
        provider,
        items,
        customerEmail,
        successUrl,
        cancelUrl,
        metadata: {
          ...metadata,
          userId: req.user?.id, // From auth middleware
        },
      });

      res.json(result);
    } catch (error) {
      console.error('Checkout creation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Complete a payment
   * POST /api/payments/complete
   */
  async completePayment(req, res) {
    try {
      const { provider, sessionId } = req.body;

      if (!provider || !sessionId) {
        return res.status(400).json({
          success: false,
          error: 'Provider and session ID are required',
        });
      }

      const result = await paymentService.completePayment(provider, sessionId);

      res.json(result);
    } catch (error) {
      console.error('Payment completion error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Get payment details
   * GET /api/payments/:provider/:id
   */
  async getPayment(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.getPayment(provider, id);

      res.json(result);
    } catch (error) {
      console.error('Get payment error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Create a subscription
   * POST /api/payments/subscriptions
   */
  async createSubscription(req, res) {
    try {
      const {
        provider = process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe',
        planId,
        customerEmail,
        trialPeriodDays = 0,
        metadata = {},
      } = req.body;

      if (!planId || !customerEmail) {
        return res.status(400).json({
          success: false,
          error: 'Plan ID and customer email are required',
        });
      }

      const baseUrl = process.env.FRONTEND_URL || 'http://localhost:3000';
      const successUrl = `${baseUrl}/subscriptions/success?session_id={CHECKOUT_SESSION_ID}`;
      const cancelUrl = `${baseUrl}/subscriptions/cancel`;

      const result = await paymentService.createSubscription({
        provider,
        planId,
        customerEmail,
        successUrl,
        cancelUrl,
        trialPeriodDays,
        metadata: {
          ...metadata,
          userId: req.user?.id,
        },
      });

      res.json(result);
    } catch (error) {
      console.error('Subscription creation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Get subscription details
   * GET /api/payments/subscriptions/:provider/:id
   */
  async getSubscription(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.getSubscription(provider, id);

      res.json(result);
    } catch (error) {
      console.error('Get subscription error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Cancel a subscription
   * POST /api/payments/subscriptions/:provider/:id/cancel
   */
  async cancelSubscription(req, res) {
    try {
      const { provider, id } = req.params;
      const { immediately = false, reason = '' } = req.body;

      const result = await paymentService.cancelSubscription(
        provider,
        id,
        immediately,
        reason
      );

      res.json(result);
    } catch (error) {
      console.error('Subscription cancellation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Reactivate a subscription
   * POST /api/payments/subscriptions/:provider/:id/reactivate
   */
  async reactivateSubscription(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.reactivateSubscription(provider, id);

      res.json(result);
    } catch (error) {
      console.error('Subscription reactivation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Create a refund
   * POST /api/payments/refunds
   */
  async createRefund(req, res) {
    try {
      const {
        provider,
        paymentId,
        amount,
        currency = 'USD',
        reason = 'requested_by_customer',
        note = '',
        metadata = {},
      } = req.body;

      if (!provider || !paymentId) {
        return res.status(400).json({
          success: false,
          error: 'Provider and payment ID are required',
        });
      }

      // TODO: Add authorization check - only admins or original purchaser

      const result = await paymentService.createRefund({
        provider,
        paymentId,
        amount,
        currency,
        reason,
        note,
        metadata: {
          ...metadata,
          refundedBy: req.user?.id,
        },
      });

      res.json(result);
    } catch (error) {
      console.error('Refund creation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Get refund details
   * GET /api/payments/refunds/:provider/:id
   */
  async getRefund(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.getRefund(provider, id);

      res.json(result);
    } catch (error) {
      console.error('Get refund error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Handle Stripe webhook
   * POST /api/webhooks/stripe
   */
  async handleStripeWebhook(req, res) {
    try {
      const result = await paymentService.handleWebhook({
        provider: 'stripe',
        headers: req.headers,
        payload: req.body, // Raw body
      });

      console.log('Stripe webhook processed:', result);

      res.json({ received: true, ...result });
    } catch (error) {
      console.error('Stripe webhook error:', error);
      res.status(400).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Handle PayPal webhook
   * POST /api/webhooks/paypal
   */
  async handlePayPalWebhook(req, res) {
    try {
      const result = await paymentService.handleWebhook({
        provider: 'paypal',
        headers: req.headers,
        payload: req.body, // Parsed JSON
      });

      console.log('PayPal webhook processed:', result);

      res.json({ received: true, ...result });
    } catch (error) {
      console.error('PayPal webhook error:', error);
      res.status(400).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Create a customer
   * POST /api/payments/customers
   */
  async createCustomer(req, res) {
    try {
      const {
        provider = process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe',
        email,
        name,
        metadata = {},
      } = req.body;

      if (!email || !name) {
        return res.status(400).json({
          success: false,
          error: 'Email and name are required',
        });
      }

      const result = await paymentService.createCustomer({
        provider,
        email,
        name,
        metadata: {
          ...metadata,
          userId: req.user?.id,
        },
      });

      res.json(result);
    } catch (error) {
      console.error('Customer creation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Get customer details
   * GET /api/payments/customers/:provider/:id
   */
  async getCustomer(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.getCustomer(provider, id);

      res.json(result);
    } catch (error) {
      console.error('Get customer error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * List payment methods
   * GET /api/payments/customers/:provider/:id/payment-methods
   */
  async listPaymentMethods(req, res) {
    try {
      const { provider, id } = req.params;

      const result = await paymentService.listPaymentMethods(provider, id);

      res.json(result);
    } catch (error) {
      console.error('List payment methods error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Validate provider configuration
   * GET /api/payments/config/validate/:provider
   */
  async validateConfig(req, res) {
    try {
      const { provider } = req.params;

      const result = paymentService.validateProviderConfig(provider);

      res.json(result);
    } catch (error) {
      console.error('Config validation error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }

  /**
   * Get supported providers
   * GET /api/payments/providers
   */
  async getSupportedProviders(req, res) {
    try {
      const providers = paymentService.getSupportedProviders();

      res.json({
        success: true,
        providers,
        defaultProvider: process.env.DEFAULT_PAYMENT_PROVIDER || 'stripe',
      });
    } catch (error) {
      console.error('Get providers error:', error);
      res.status(500).json({
        success: false,
        error: error.message,
      });
    }
  }
}

export default new PaymentController();
