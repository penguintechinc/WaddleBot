/**
 * Order Service
 * Example integration showing how to connect payment services with database
 * This demonstrates the complete flow from checkout to fulfillment
 */

import paymentService from './paymentService.js';

class OrderService {
  /**
   * Create an order and initiate payment
   * @param {Object} orderData - Order information
   * @returns {Promise<Object>} Order with payment URL
   */
  async createOrder(orderData) {
    const {
      userId,
      items,
      customerEmail,
      customerName,
      paymentProvider = 'stripe',
    } = orderData;

    try {
      // 1. Validate order data
      if (!items || items.length === 0) {
        throw new Error('Order must contain at least one item');
      }

      // 2. Calculate order totals
      const subtotal = items.reduce((sum, item) => {
        return sum + (item.price * (item.quantity || 1));
      }, 0);

      const tax = subtotal * 0.1; // Example: 10% tax
      const total = subtotal + tax;

      // 3. Create order record in database
      // TODO: Replace with your actual database implementation
      const order = {
        id: `order_${Date.now()}`,
        userId,
        customerEmail,
        customerName,
        items,
        subtotal,
        tax,
        total,
        status: 'pending',
        paymentProvider,
        paymentStatus: 'pending',
        createdAt: new Date(),
      };

      console.log('Order created:', order.id);
      // await db.orders.insert(order);

      // 4. Create payment checkout session
      const checkout = await paymentService.createCheckout({
        provider: paymentProvider,
        items: items.map(item => ({
          name: item.name,
          description: item.description,
          price: item.price,
          quantity: item.quantity || 1,
          currency: item.currency || 'usd',
          images: item.images || [],
        })),
        customerEmail,
        successUrl: `${process.env.FRONTEND_URL}/orders/${order.id}/success?session_id={CHECKOUT_SESSION_ID}`,
        cancelUrl: `${process.env.FRONTEND_URL}/orders/${order.id}/cancel`,
        metadata: {
          orderId: order.id,
          userId,
        },
      });

      // 5. Update order with payment session ID
      order.paymentSessionId = checkout.sessionId;
      order.checkoutUrl = checkout.url;

      console.log('Payment session created:', checkout.sessionId);
      // await db.orders.update(order.id, { paymentSessionId: checkout.sessionId });

      return {
        success: true,
        order,
        checkoutUrl: checkout.url,
      };
    } catch (error) {
      console.error('Order creation error:', error);
      throw error;
    }
  }

  /**
   * Process successful payment (called from webhook)
   * @param {Object} paymentData - Payment data from webhook
   * @returns {Promise<Object>} Updated order
   */
  async processPaymentSuccess(paymentData) {
    const { orderId, sessionId, paymentProvider } = paymentData;

    try {
      console.log(`Processing successful payment for order ${orderId}`);

      // 1. Get order from database
      // const order = await db.orders.findById(orderId);
      const order = { id: orderId }; // Placeholder

      if (!order) {
        throw new Error(`Order not found: ${orderId}`);
      }

      // 2. Verify payment details match
      if (order.paymentSessionId !== sessionId) {
        throw new Error('Payment session ID mismatch');
      }

      // 3. Update order status
      const updates = {
        status: 'paid',
        paymentStatus: 'succeeded',
        paidAt: new Date(),
        paymentDetails: paymentData,
      };

      console.log('Updating order status to paid');
      // await db.orders.update(orderId, updates);

      // 4. Fulfill the order
      await this.fulfillOrder(orderId);

      // 5. Send confirmation email
      await this.sendOrderConfirmation(orderId);

      return {
        success: true,
        orderId,
        status: 'paid',
      };
    } catch (error) {
      console.error('Payment processing error:', error);

      // Update order with error
      // await db.orders.update(orderId, {
      //   status: 'payment_failed',
      //   paymentError: error.message,
      // });

      throw error;
    }
  }

  /**
   * Process failed payment (called from webhook)
   * @param {Object} paymentData - Payment data from webhook
   * @returns {Promise<Object>} Updated order
   */
  async processPaymentFailure(paymentData) {
    const { orderId, failureReason } = paymentData;

    try {
      console.log(`Processing failed payment for order ${orderId}`);

      // Update order status
      const updates = {
        status: 'payment_failed',
        paymentStatus: 'failed',
        paymentError: failureReason,
        failedAt: new Date(),
      };

      // await db.orders.update(orderId, updates);

      // Send failure notification email
      await this.sendPaymentFailureNotification(orderId);

      return {
        success: true,
        orderId,
        status: 'payment_failed',
      };
    } catch (error) {
      console.error('Payment failure processing error:', error);
      throw error;
    }
  }

  /**
   * Fulfill an order (activate purchased items)
   * @param {string} orderId - Order ID
   * @returns {Promise<void>}
   */
  async fulfillOrder(orderId) {
    try {
      console.log(`Fulfilling order ${orderId}`);

      // TODO: Implement your fulfillment logic
      // Examples:
      // - Activate bot extension/plugin
      // - Grant access to premium features
      // - Send download links
      // - Update user subscription
      // - Activate license key

      // const order = await db.orders.findById(orderId);
      // for (const item of order.items) {
      //   if (item.type === 'extension') {
      //     await this.activateExtension(order.userId, item.extensionId);
      //   } else if (item.type === 'subscription') {
      //     await this.activateSubscription(order.userId, item.planId);
      //   }
      // }

      // await db.orders.update(orderId, {
      //   fulfillmentStatus: 'fulfilled',
      //   fulfilledAt: new Date(),
      // });

      console.log(`Order ${orderId} fulfilled successfully`);
    } catch (error) {
      console.error('Order fulfillment error:', error);
      // await db.orders.update(orderId, {
      //   fulfillmentStatus: 'failed',
      //   fulfillmentError: error.message,
      // });
      throw error;
    }
  }

  /**
   * Send order confirmation email
   * @param {string} orderId - Order ID
   * @returns {Promise<void>}
   */
  async sendOrderConfirmation(orderId) {
    try {
      console.log(`Sending confirmation email for order ${orderId}`);

      // TODO: Implement email sending
      // const order = await db.orders.findById(orderId);
      // await emailService.send({
      //   to: order.customerEmail,
      //   subject: 'Order Confirmation',
      //   template: 'order-confirmation',
      //   data: { order },
      // });
    } catch (error) {
      console.error('Email sending error:', error);
      // Don't throw - email failure shouldn't fail the order
    }
  }

  /**
   * Send payment failure notification
   * @param {string} orderId - Order ID
   * @returns {Promise<void>}
   */
  async sendPaymentFailureNotification(orderId) {
    try {
      console.log(`Sending payment failure notification for order ${orderId}`);

      // TODO: Implement email sending
      // const order = await db.orders.findById(orderId);
      // await emailService.send({
      //   to: order.customerEmail,
      //   subject: 'Payment Failed',
      //   template: 'payment-failed',
      //   data: { order },
      // });
    } catch (error) {
      console.error('Email sending error:', error);
    }
  }

  /**
   * Process a refund request
   * @param {Object} refundData - Refund request data
   * @returns {Promise<Object>} Refund result
   */
  async processRefund(refundData) {
    const { orderId, amount, reason, requestedBy } = refundData;

    try {
      console.log(`Processing refund for order ${orderId}`);

      // 1. Get order
      // const order = await db.orders.findById(orderId);
      const order = { id: orderId, paymentProvider: 'stripe', total: 100 }; // Placeholder

      if (!order) {
        throw new Error(`Order not found: ${orderId}`);
      }

      if (order.status !== 'paid') {
        throw new Error('Order must be paid to process refund');
      }

      // 2. Validate refund amount
      const refundAmount = amount || order.total;
      if (refundAmount > order.total) {
        throw new Error('Refund amount exceeds order total');
      }

      // 3. Create refund via payment provider
      const refund = await paymentService.createRefund({
        provider: order.paymentProvider,
        paymentId: order.paymentIntentId,
        amount: refundAmount,
        reason,
        metadata: {
          orderId,
          requestedBy,
        },
      });

      // 4. Update order
      const updates = {
        status: amount >= order.total ? 'refunded' : 'partially_refunded',
        refundStatus: refund.status,
        refundId: refund.refundId,
        refundAmount: refundAmount,
        refundedAt: new Date(),
        refundReason: reason,
      };

      // await db.orders.update(orderId, updates);

      // 5. Revoke access if full refund
      if (refundAmount >= order.total) {
        await this.revokeOrderAccess(orderId);
      }

      // 6. Send refund confirmation
      await this.sendRefundConfirmation(orderId);

      return {
        success: true,
        orderId,
        refund,
      };
    } catch (error) {
      console.error('Refund processing error:', error);
      throw error;
    }
  }

  /**
   * Revoke access granted by an order
   * @param {string} orderId - Order ID
   * @returns {Promise<void>}
   */
  async revokeOrderAccess(orderId) {
    try {
      console.log(`Revoking access for order ${orderId}`);

      // TODO: Implement access revocation
      // const order = await db.orders.findById(orderId);
      // for (const item of order.items) {
      //   if (item.type === 'extension') {
      //     await this.deactivateExtension(order.userId, item.extensionId);
      //   } else if (item.type === 'subscription') {
      //     await this.cancelSubscription(order.userId, item.subscriptionId);
      //   }
      // }

      console.log(`Access revoked for order ${orderId}`);
    } catch (error) {
      console.error('Access revocation error:', error);
      throw error;
    }
  }

  /**
   * Send refund confirmation email
   * @param {string} orderId - Order ID
   * @returns {Promise<void>}
   */
  async sendRefundConfirmation(orderId) {
    try {
      console.log(`Sending refund confirmation for order ${orderId}`);

      // TODO: Implement email sending
    } catch (error) {
      console.error('Email sending error:', error);
    }
  }

  /**
   * Get order details
   * @param {string} orderId - Order ID
   * @returns {Promise<Object>} Order details
   */
  async getOrder(orderId) {
    try {
      // const order = await db.orders.findById(orderId);
      const order = { id: orderId }; // Placeholder

      if (!order) {
        throw new Error(`Order not found: ${orderId}`);
      }

      return {
        success: true,
        order,
      };
    } catch (error) {
      console.error('Get order error:', error);
      throw error;
    }
  }

  /**
   * Get orders for a user
   * @param {string} userId - User ID
   * @param {Object} options - Query options
   * @returns {Promise<Object>} User orders
   */
  async getUserOrders(userId, options = {}) {
    try {
      const { limit = 10, offset = 0, status } = options;

      // const query = { userId };
      // if (status) query.status = status;

      // const orders = await db.orders.find(query)
      //   .limit(limit)
      //   .offset(offset)
      //   .orderBy('createdAt', 'desc');

      const orders = []; // Placeholder

      return {
        success: true,
        orders,
        total: orders.length,
      };
    } catch (error) {
      console.error('Get user orders error:', error);
      throw error;
    }
  }

  /**
   * Update webhook handler in payment services to call order service
   * This method should be called from the webhook handlers in stripeService and paypalService
   */
  static getWebhookHandlers() {
    return {
      onCheckoutCompleted: async (sessionData) => {
        const orderService = new OrderService();
        const orderId = sessionData.metadata?.orderId;

        if (orderId) {
          await orderService.processPaymentSuccess({
            orderId,
            sessionId: sessionData.sessionId,
            paymentProvider: 'stripe',
            amount: sessionData.amountTotal,
            customerEmail: sessionData.customerEmail,
          });
        }
      },

      onPaymentFailed: async (paymentData) => {
        const orderService = new OrderService();
        const orderId = paymentData.metadata?.orderId;

        if (orderId) {
          await orderService.processPaymentFailure({
            orderId,
            failureReason: paymentData.failureMessage,
          });
        }
      },
    };
  }
}

export default new OrderService();
