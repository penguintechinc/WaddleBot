import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import express from 'express';
import request from 'supertest';

import paymentController from '../paymentController.js';
import paymentService from '../../services/paymentService.js';

describe('PaymentController.createRefund', () => {
  let app;
  let authenticatedUser;
  let createRefundSpy;
  let getRefundablePaymentSpy;

  const refundRequest = {
    provider: 'stripe',
    paymentId: 'cs_test123',
    amount: 100,
    metadata: {
      requestId: 'request-123',
    },
  };

  beforeEach(() => {
    authenticatedUser = null;
    getRefundablePaymentSpy = jest.spyOn(paymentService, 'getRefundablePayment');
    createRefundSpy = jest.spyOn(paymentService, 'createRefund');

    app = express();
    app.use(express.json());

    // Authentication must run before the route under test.
    app.use((req, _res, next) => {
      if (authenticatedUser) {
        req.user = authenticatedUser;
      }
      next();
    });

    app.post(
      '/refunds',
      paymentController.createRefund.bind(paymentController),
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('rejects an unauthenticated refund request', async () => {
    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(403);
    expect(response.body).toEqual({
      success: false,
      error: 'Authentication required to create refunds',
    });
    expect(getRefundablePaymentSpy).not.toHaveBeenCalled();
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('rejects a user who is neither the payment owner nor an admin', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: {
        id: 'ch_test123',
        metadata: {
          userId: 'user-456',
        },
      },
      ownerId: 'user-456',
      refundablePaymentId: 'pi_test123',
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(403);
    expect(response.body).toEqual({
      success: false,
      error: 'Not authorized to refund this payment',
    });
    expect(getRefundablePaymentSpy).toHaveBeenCalledWith('stripe', 'cs_test123');
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('allows the payment owner and records who initiated the refund', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: {
        id: 'ch_test123',
        metadata: {
          userId: authenticatedUser.id,
        },
      },
      ownerId: authenticatedUser.id,
      refundablePaymentId: 'pi_test123',
    });
    createRefundSpy.mockResolvedValue({
      success: true,
      refundId: 'ref_test123',
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      success: true,
      refundId: 'ref_test123',
    });
    expect(createRefundSpy).toHaveBeenCalledWith({
      provider: 'stripe',
      paymentId: 'pi_test123',
      amount: 100,
      currency: 'USD',
      reason: 'requested_by_customer',
      note: '',
      metadata: {
        requestId: 'request-123',
        refundedBy: authenticatedUser.id,
      },
    });
  });

  it.each([
    ['super_admin role', { roles: ['super_admin'], isSuperAdmin: false }],
    ['platform-admin role', { roles: ['platform-admin'], isSuperAdmin: false }],
    ['super-admin flag', { roles: [], isSuperAdmin: true }],
  ])('allows an admin identified by %s', async (_description, adminClaims) => {
    authenticatedUser = {
      id: 'admin-123',
      ...adminClaims,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: {
        id: 'ch_test123',
        metadata: {
          userId: 'user-456',
        },
      },
      ownerId: 'user-456',
      refundablePaymentId: 'pi_test123',
    });
    createRefundSpy.mockResolvedValue({
      success: true,
      refundId: 'ref_test123',
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      success: true,
      refundId: 'ref_test123',
    });
    expect(createRefundSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'stripe',
        paymentId: 'pi_test123',
        metadata: {
          requestId: 'request-123',
          refundedBy: authenticatedUser.id,
        },
      }),
    );
  });

  it('returns not found when the referenced payment does not exist', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue(null);

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(404);
    expect(response.body).toEqual({
      success: false,
      error: 'Payment not found',
    });
    expect(getRefundablePaymentSpy).toHaveBeenCalledWith('stripe', 'cs_test123');
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('resolves a PayPal order to its capture before refunding', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: {
        id: 'PAYPAL-ORDER-123',
        purchase_units: [{
          custom_id: authenticatedUser.id,
          payments: {
            captures: [{ id: 'PAYPAL-CAPTURE-123', status: 'COMPLETED' }],
          },
        }],
      },
      ownerId: authenticatedUser.id,
      refundablePaymentId: 'PAYPAL-CAPTURE-123',
    });
    createRefundSpy.mockResolvedValue({
      success: true,
      refundId: 'PAYPAL-REFUND-123',
    });

    const response = await request(app).post('/refunds').send({
      ...refundRequest,
      provider: 'paypal',
      paymentId: 'PAYPAL-ORDER-123',
    });

    expect(response.status).toBe(200);
    expect(getRefundablePaymentSpy).toHaveBeenCalledWith('paypal', 'PAYPAL-ORDER-123');
    expect(createRefundSpy).toHaveBeenCalledWith(expect.objectContaining({
      provider: 'paypal',
      paymentId: 'PAYPAL-CAPTURE-123',
    }));
  });

  it('rejects a checkout that has not produced a refundable payment', async () => {
    authenticatedUser = {
      id: 'admin-123',
      roles: ['super_admin'],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: { id: 'cs_test123' },
      ownerId: undefined,
      refundablePaymentId: undefined,
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(400);
    expect(response.body).toEqual({
      success: false,
      error: 'Payment has not been captured and cannot be refunded',
    });
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('does not treat missing ownership metadata as payment ownership', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getRefundablePaymentSpy.mockResolvedValue({
      payment: { id: 'cs_test123' },
      ownerId: undefined,
      refundablePaymentId: 'pi_test123',
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(403);
    expect(response.body).toEqual({
      success: false,
      error: 'Not authorized to refund this payment',
    });
    expect(createRefundSpy).not.toHaveBeenCalled();
  });
});

describe('PaymentService.getRefundablePayment', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('extracts the PaymentIntent and owner from a Stripe Checkout Session', async () => {
    jest.spyOn(paymentService, 'getPayment').mockResolvedValue({
      success: true,
      session: {
        id: 'cs_test123',
        metadata: { userId: 'user-123' },
        payment_intent: { id: 'pi_test123' },
      },
    });

    await expect(
      paymentService.getRefundablePayment('Stripe', 'cs_test123'),
    ).resolves.toEqual({
      payment: expect.objectContaining({ id: 'cs_test123' }),
      ownerId: 'user-123',
      refundablePaymentId: 'pi_test123',
    });
    expect(paymentService.getPayment).toHaveBeenCalledWith('stripe', 'cs_test123');
  });

  it('extracts the completed capture and owner from a PayPal Order', async () => {
    jest.spyOn(paymentService, 'getPayment').mockResolvedValue({
      success: true,
      order: {
        id: 'PAYPAL-ORDER-123',
        purchase_units: [{
          custom_id: 'user-123',
          payments: {
            captures: [
              { id: 'CAPTURE-PENDING', status: 'PENDING' },
              { id: 'CAPTURE-COMPLETED', status: 'COMPLETED' },
            ],
          },
        }],
      },
    });

    await expect(
      paymentService.getRefundablePayment('PayPal', 'PAYPAL-ORDER-123'),
    ).resolves.toEqual({
      payment: expect.objectContaining({ id: 'PAYPAL-ORDER-123' }),
      ownerId: 'user-123',
      refundablePaymentId: 'CAPTURE-COMPLETED',
    });
    expect(paymentService.getPayment).toHaveBeenCalledWith('paypal', 'PAYPAL-ORDER-123');
  });
});
