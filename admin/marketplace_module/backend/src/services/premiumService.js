/**
 * Premium Service — Community Premium subscription management
 */
import { query, transaction } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';
import stripeService from './stripeService.js';

export async function getPricingConfig() {
  const { rows } = await query(
    `SELECT setting_key, setting_value FROM marketplace_settings
     WHERE setting_key IN (
       'community_premium_base_price_cents',
       'community_premium_base_seat_limit',
       'community_premium_overage_price_cents'
     )`
  );

  const config = Object.fromEntries(rows.map((r) => [r.setting_key, r.setting_value]));

  return {
    basePriceCents: parseInt(config['community_premium_base_price_cents']) || 0,
    baseSeatLimit: parseInt(config['community_premium_base_seat_limit']) || 0,
    overagePriceCents: parseInt(config['community_premium_overage_price_cents']) || 0,
  };
}

export async function getSubscriptionStatus(communityId) {
  const { rows } = await query(
    `SELECT cps.*, c.is_premium, c.seat_limit
     FROM community_premium_subscriptions cps
     JOIN communities c ON c.id = cps.community_id
     WHERE cps.community_id = $1
     LIMIT 1`,
    [communityId]
  );

  return rows[0] || null;
}

export async function getCurrentSeatCount(communityId) {
  const { rows } = await query(
    `SELECT COUNT(*) AS count FROM community_members
     WHERE community_id = $1 AND is_active = true`,
    [communityId]
  );

  return parseInt(rows[0].count);
}

export function calculateMonthlyBill(seatCount, basePriceCents, baseSeatLimit, overagePriceCents) {
  return basePriceCents + Math.max(0, seatCount - baseSeatLimit) * overagePriceCents;
}

export async function subscribeCommunityPremium(
  communityId,
  provider = 'stripe',
  successUrl,
  cancelUrl
) {
  const { basePriceCents, baseSeatLimit, overagePriceCents } = await getPricingConfig();
  const seatCount = await getCurrentSeatCount(communityId);
  const total = calculateMonthlyBill(seatCount, basePriceCents, baseSeatLimit, overagePriceCents);

  let checkout;

  if (provider === 'stripe') {
    checkout = await stripeService.createCheckoutSession({
      items: [
        {
          name: 'WaddleBot Community Premium',
          description: `${seatCount} seats`,
          price: total / 100,
          currency: 'usd',
          quantity: 1,
        },
      ],
      customerEmail: null,
      successUrl,
      cancelUrl,
      metadata: {
        communityId: String(communityId),
        type: 'community_premium',
      },
    });
  }

  await query(
    `INSERT INTO community_premium_subscriptions
       (community_id, status, base_price_cents, overage_price_cents, base_seat_limit, current_seat_count, created_at, updated_at)
     VALUES ($1, 'trialing', $2, $3, $4, $5, NOW(), NOW())
     ON CONFLICT (community_id) DO UPDATE
       SET status='trialing',
           current_seat_count=EXCLUDED.current_seat_count,
           updated_at=NOW()`,
    [communityId, basePriceCents, overagePriceCents, baseSeatLimit, seatCount]
  );

  return {
    checkoutUrl: checkout.url,
    sessionId: checkout.sessionId,
    pricing: {
      basePriceCents,
      seatCount,
      totalCents: total,
    },
  };
}

export async function cancelCommunityPremium(communityId, immediately = false) {
  const sub = await getSubscriptionStatus(communityId);

  if (!sub) {
    throw errors.notFound('No premium subscription found');
  }

  if (sub.stripe_subscription_id) {
    await stripeService.cancelSubscription(sub.stripe_subscription_id, immediately);
  }

  await query(
    `UPDATE community_premium_subscriptions
     SET status='canceled', cancel_at_period_end=true, updated_at=NOW()
     WHERE community_id=$1`,
    [communityId]
  );

  if (immediately) {
    await query(
      `UPDATE communities SET is_premium=false WHERE id=$1`,
      [communityId]
    );
  }

  return { success: true, cancelAtPeriodEnd: !immediately };
}

export async function syncSeatCount(communityId) {
  const seatCount = await getCurrentSeatCount(communityId);

  await query(
    `UPDATE community_premium_subscriptions
     SET current_seat_count=$1, updated_at=NOW()
     WHERE community_id=$2`,
    [seatCount, communityId]
  );

  return seatCount;
}
