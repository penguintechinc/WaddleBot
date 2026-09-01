import { Router } from 'express';
import paymentController from '../controllers/paymentController.js';
import { requireAuth } from '../middleware/auth.js';

/**
 * Payment Routes
 * All routes for payment operations
 */
const router = Router();

// Checkout and payments
router.post('/checkout', paymentController.createCheckout.bind(paymentController));
router.post('/complete', paymentController.completePayment.bind(paymentController));
router.get('/:provider/:id', paymentController.getPayment.bind(paymentController));

// Subscriptions
router.post('/subscriptions', paymentController.createSubscription.bind(paymentController));
router.get('/subscriptions/:provider/:id', paymentController.getSubscription.bind(paymentController));
router.post('/subscriptions/:provider/:id/cancel', paymentController.cancelSubscription.bind(paymentController));
router.post('/subscriptions/:provider/:id/reactivate', paymentController.reactivateSubscription.bind(paymentController));

// Refunds
router.post('/refunds', requireAuth, paymentController.createRefund.bind(paymentController));
router.get('/refunds/:provider/:id', paymentController.getRefund.bind(paymentController));

// Customers
router.post('/customers', paymentController.createCustomer.bind(paymentController));
router.get('/customers/:provider/:id', paymentController.getCustomer.bind(paymentController));
router.get('/customers/:provider/:id/payment-methods', paymentController.listPaymentMethods.bind(paymentController));

// Configuration
router.get('/providers', paymentController.getSupportedProviders.bind(paymentController));
router.get('/config/validate/:provider', paymentController.validateConfig.bind(paymentController));

export default router;
