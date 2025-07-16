import { apiClient } from './apiClient';
import { ENDPOINTS, PAYMENT_CONFIG } from '../constants/config';

class PaymentService {
  // Payment Methods Management
  async getPaymentMethods(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.PAYMENT_METHODS}?communityId=${communityId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting payment methods:', error);
      throw error;
    }
  }

  async savePaymentMethod(communityId, paymentData) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_METHODS, {
        communityId,
        ...paymentData,
      });
      return response.data;
    } catch (error) {
      console.error('Error saving payment method:', error);
      throw error;
    }
  }

  async deletePaymentMethod(communityId, paymentMethodId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.PAYMENT_METHODS}/${paymentMethodId}?communityId=${communityId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting payment method:', error);
      throw error;
    }
  }

  // Payment Processing
  async processPayment(paymentData) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_PROCESS, {
        ...paymentData,
        timestamp: new Date().toISOString(),
      });
      return response.data;
    } catch (error) {
      console.error('Error processing payment:', error);
      throw error;
    }
  }

  async verifyPayment(paymentId) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_VERIFY, {
        paymentId,
      });
      return response.data;
    } catch (error) {
      console.error('Error verifying payment:', error);
      throw error;
    }
  }

  // Payment History
  async getPaymentHistory(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      params.append('communityId', communityId);
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.status) params.append('status', options.status);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.PAYMENT_HISTORY}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting payment history:', error);
      throw error;
    }
  }

  // PayPal Integration
  async initializePayPalPayment(communityId, moduleId, amount, currency = 'USD') {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_PROCESS, {
        provider: 'paypal',
        communityId,
        moduleId,
        amount,
        currency,
        type: 'module_purchase',
        returnUrl: `waddlebot://payment/success`,
        cancelUrl: `waddlebot://payment/cancel`,
      });
      return response.data;
    } catch (error) {
      console.error('Error initializing PayPal payment:', error);
      throw error;
    }
  }

  async executePayPalPayment(paymentId, payerId) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_VERIFY, {
        provider: 'paypal',
        paymentId,
        payerId,
      });
      return response.data;
    } catch (error) {
      console.error('Error executing PayPal payment:', error);
      throw error;
    }
  }

  // Stripe Integration
  async initializeStripePayment(communityId, moduleId, amount, currency = 'USD') {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_PROCESS, {
        provider: 'stripe',
        communityId,
        moduleId,
        amount,
        currency,
        type: 'module_purchase',
      });
      return response.data;
    } catch (error) {
      console.error('Error initializing Stripe payment:', error);
      throw error;
    }
  }

  async confirmStripePayment(paymentIntentId) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_VERIFY, {
        provider: 'stripe',
        paymentIntentId,
      });
      return response.data;
    } catch (error) {
      console.error('Error confirming Stripe payment:', error);
      throw error;
    }
  }

  // Module Purchase
  async purchaseModule(communityId, moduleId, paymentMethod, paymentData) {
    try {
      const response = await apiClient.post(ENDPOINTS.PAYMENT_PROCESS, {
        type: 'module_purchase',
        communityId,
        moduleId,
        paymentMethod,
        ...paymentData,
        timestamp: new Date().toISOString(),
      });
      return response.data;
    } catch (error) {
      console.error('Error purchasing module:', error);
      throw error;
    }
  }

  // Payment Validation
  validatePaymentAmount(amount) {
    const numAmount = parseFloat(amount);
    return !isNaN(numAmount) && 
           numAmount >= PAYMENT_CONFIG.MIN_TRANSACTION && 
           numAmount <= PAYMENT_CONFIG.MAX_TRANSACTION;
  }

  validateCurrency(currency) {
    return PAYMENT_CONFIG.SUPPORTED_CURRENCIES.includes(currency.toUpperCase());
  }

  // Payment Formatting
  formatPaymentAmount(amount, currency = PAYMENT_CONFIG.DEFAULT_CURRENCY) {
    const numAmount = parseFloat(amount) || 0;
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(numAmount);
  }

  formatPaymentDate(dateString) {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  // Payment Status
  getPaymentStatusColor(status) {
    const statusColors = {
      pending: '#FF9800',
      processing: '#2196F3',
      completed: '#4CAF50',
      failed: '#F44336',
      cancelled: '#757575',
      refunded: '#9C27B0',
    };
    return statusColors[status] || '#757575';
  }

  getPaymentStatusIcon(status) {
    const statusIcons = {
      pending: '⏳',
      processing: '⚙️',
      completed: '✅',
      failed: '❌',
      cancelled: '🚫',
      refunded: '↩️',
    };
    return statusIcons[status] || '📝';
  }

  getPaymentMethodIcon(method) {
    const methodIcons = {
      paypal: '🏦',
      stripe: '💳',
      credit_card: '💳',
      debit_card: '💳',
      bank_transfer: '🏦',
      wallet: '👛',
    };
    return methodIcons[method] || '💰';
  }

  // Payment Error Handling
  handlePaymentError(error) {
    console.error('Payment error:', error);
    
    if (error.response) {
      const { status, data } = error.response;
      
      switch (status) {
        case 400:
          return 'Invalid payment information. Please check your details and try again.';
        case 401:
          return 'Payment authentication failed. Please try again.';
        case 402:
          return 'Payment required. Please ensure you have sufficient funds.';
        case 403:
          return 'Payment not authorized. Please contact support.';
        case 404:
          return 'Payment method not found. Please select a valid payment method.';
        case 409:
          return 'Payment already processed. Please check your transaction history.';
        case 422:
          return data.message || 'Payment validation failed. Please check your information.';
        case 500:
          return 'Payment system error. Please try again later.';
        case 503:
          return 'Payment service temporarily unavailable. Please try again later.';
        default:
          return data.message || 'Payment processing failed. Please try again.';
      }
    }
    
    if (error.request) {
      return 'Network error. Please check your connection and try again.';
    }
    
    return 'Unexpected error occurred. Please try again.';
  }

  // Payment Receipt
  async generatePaymentReceipt(paymentId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.PAYMENT_HISTORY}/${paymentId}/receipt`
      );
      return response.data;
    } catch (error) {
      console.error('Error generating payment receipt:', error);
      throw error;
    }
  }

  // Payment Refund
  async requestRefund(paymentId, reason) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.PAYMENT_HISTORY}/${paymentId}/refund`,
        {
          reason,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error requesting refund:', error);
      throw error;
    }
  }

  // Payment Analytics
  async getPaymentAnalytics(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      params.append('communityId', communityId);
      if (options.period) params.append('period', options.period);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.PAYMENT_HISTORY}/analytics?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting payment analytics:', error);
      throw error;
    }
  }
}

export const paymentService = new PaymentService();