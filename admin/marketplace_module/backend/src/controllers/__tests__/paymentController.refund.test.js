import { afterEach, beforeEach, describe, expect, it, jest } from '@jest/globals';
import express from 'express';
import request from 'supertest';

import paymentController from '../paymentController.js';
import paymentService from '../../services/paymentService.js';

describe('PaymentController.createRefund', () => {
  let app;
  let authenticatedUser;
  let createRefundSpy;
  let getPaymentSpy;

  const refundRequest = {
    provider: 'stripe',
    paymentId: 'pi_test123',
    amount: 100,
    metadata: {
      requestId: 'request-123',
    },
  };

  beforeEach(() => {
    authenticatedUser = null;
    getPaymentSpy = jest.spyOn(paymentService, 'getPayment');
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
    expect(getPaymentSpy).not.toHaveBeenCalled();
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('rejects a user who is neither the payment owner nor an admin', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getPaymentSpy.mockResolvedValue({
      session: {
        id: 'ch_test123',
        metadata: {
          userId: 'user-456',
        },
      },
    });

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(403);
    expect(response.body).toEqual({
      success: false,
      error: 'Not authorized to refund this payment',
    });
    expect(getPaymentSpy).toHaveBeenCalledWith('stripe', 'pi_test123');
    expect(createRefundSpy).not.toHaveBeenCalled();
  });

  it('allows the payment owner and records who initiated the refund', async () => {
    authenticatedUser = {
      id: 'user-123',
      roles: [],
      isSuperAdmin: false,
    };
    getPaymentSpy.mockResolvedValue({
      session: {
        id: 'ch_test123',
        metadata: {
          userId: authenticatedUser.id,
        },
      },
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
    getPaymentSpy.mockResolvedValue({
      session: {
        id: 'ch_test123',
        metadata: {
          userId: 'user-456',
        },
      },
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
    getPaymentSpy.mockResolvedValue(null);

    const response = await request(app).post('/refunds').send(refundRequest);

    expect(response.status).toBe(404);
    expect(response.body).toEqual({
      success: false,
      error: 'Payment not found',
    });
    expect(getPaymentSpy).toHaveBeenCalledWith('stripe', 'pi_test123');
    expect(createRefundSpy).not.toHaveBeenCalled();
  });
});
