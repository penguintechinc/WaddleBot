/**
 * Analytics Service - Proxy to analytics-core module
 */
import axios from 'axios';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';

const client = axios.create({
  baseURL: config.modules.analyticsCore,
  timeout: 10000,
  headers: {
    'X-Service-Key': config.serviceApiKey,
  },
});

function userHeaders(callerId, callerRole) {
  return {
    'X-Caller-User-ID': String(callerId),
    'X-Caller-Role': callerRole || 'user',
  };
}

// Platform analytics
export async function getPlatformSummary() {
  const res = await client.get('/api/v1/analytics/platform/summary');
  return res.data;
}

export async function getReputationDistribution() {
  const res = await client.get('/api/v1/analytics/platform/reputation');
  return res.data;
}

export async function getGrowthTrends(period = '90d') {
  const res = await client.get('/api/v1/analytics/platform/growth', { params: { period } });
  return res.data;
}

export async function getActivityBreakdown() {
  const res = await client.get('/api/v1/analytics/platform/activity');
  return res.data;
}

export async function getCommunityHealthSummaries(limit = 50) {
  const res = await client.get('/api/v1/analytics/platform/community-health', { params: { limit } });
  return res.data;
}

// User analytics
export async function getUserSelfStats(hubUserId, callerId, callerRole) {
  const res = await client.get(`/api/v1/analytics/user/${hubUserId}/self`, {
    headers: userHeaders(callerId, callerRole),
  });
  return res.data;
}

export async function getUserCommunityStats(hubUserId, communityId, callerId, callerRole) {
  const res = await client.get(`/api/v1/analytics/user/${hubUserId}/in-community/${communityId}`, {
    headers: userHeaders(callerId, callerRole),
  });
  return res.data;
}

export async function getUserReputation(hubUserId, callerId, callerRole) {
  const res = await client.get(`/api/v1/analytics/user/${hubUserId}/reputation`, {
    headers: userHeaders(callerId, callerRole),
  });
  return res.data;
}
