/**
 * Community Polls Controller
 * Proxies requests to the engagement_module service for poll management
 */
import axios from 'axios';
import logger from '../utils/logger.js';

const ENGAGEMENT_URL = process.env.ENGAGEMENT_MODULE_URL || 'http://core-engagement:8091';

/**
 * Get all polls for a community
 */
export async function getPolls(req, res) {
  try {
    const { communityId } = req.params;
    const response = await axios.get(`${ENGAGEMENT_URL}/api/v1/polls`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, polls: response.data.polls || [] });
  } catch (error) {
    logger.error('Failed to get polls:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, polls: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get polls'
    });
  }
}

/**
 * Get a specific poll with results
 */
export async function getPoll(req, res) {
  try {
    const { communityId, pollId } = req.params;
    if (!/^\d+$/.test(pollId)) {
      return res.status(400).json({ success: false, error: 'pollId must be a positive integer' });
    }
    const response = await axios.get(`${ENGAGEMENT_URL}/api/v1/polls/${pollId}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, poll: response.data.poll });
  } catch (error) {
    logger.error('Failed to get poll:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get poll'
    });
  }
}

/**
 * Create a new poll
 */
export async function createPoll(req, res) {
  try {
    const { communityId } = req.params;
    const {
      title,
      description,
      options,
      view_visibility,
      submit_visibility,
      allow_multiple_choices,
      max_choices,
      expires_at
    } = req.body;

    const response = await axios.post(`${ENGAGEMENT_URL}/api/v1/polls`, {
      community_id: communityId,
      title,
      description,
      options,
      view_visibility: view_visibility || 'community',
      submit_visibility: submit_visibility || 'community',
      allow_multiple_choices: allow_multiple_choices || false,
      max_choices: max_choices || 1,
      expires_at
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.status(201).json({ success: true, poll: response.data.poll });
  } catch (error) {
    logger.error('Failed to create poll:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to create poll'
    });
  }
}

/**
 * Delete a poll
 */
export async function deletePoll(req, res) {
  try {
    const { communityId, pollId } = req.params;
    if (!/^\d+$/.test(pollId)) {
      return res.status(400).json({ success: false, error: 'pollId must be a positive integer' });
    }
    await axios.delete(`${ENGAGEMENT_URL}/api/v1/polls/${pollId}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Poll deleted' });
  } catch (error) {
    logger.error('Failed to delete poll:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to delete poll'
    });
  }
}
