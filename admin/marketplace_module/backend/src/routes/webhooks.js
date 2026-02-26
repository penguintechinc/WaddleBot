import { Router } from 'express';
import paymentController from '../controllers/paymentController.js';

/**
 * Webhook Routes
 * Routes for payment provider webhooks
 *
 * IMPORTANT: Stripe webhooks require raw body, PayPal webhooks use JSON
 * Configure middleware accordingly in server.js
 */
const router = Router();

// Stripe webhook - requires raw body
router.post('/stripe', paymentController.handleStripeWebhook.bind(paymentController));

// PayPal webhook - uses parsed JSON
router.post('/paypal', paymentController.handlePayPalWebhook.bind(paymentController));

export default router;
