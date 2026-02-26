/**
 * Community Forms Controller
 * Proxies requests to the engagement_module service for form management
 */
import axios from 'axios';
import logger from '../utils/logger.js';

const ENGAGEMENT_URL = process.env.ENGAGEMENT_MODULE_URL || 'http://core-engagement:8091';

/**
 * Get all forms for a community
 */
export async function getForms(req, res) {
  try {
    const { communityId } = req.params;
    const response = await axios.get(`${ENGAGEMENT_URL}/api/v1/forms`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, forms: response.data.forms || [] });
  } catch (error) {
    logger.error('Failed to get forms:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, forms: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get forms'
    });
  }
}

/**
 * Get a specific form
 */
export async function getForm(req, res) {
  try {
    const { communityId, formId } = req.params;
    const response = await axios.get(`${ENGAGEMENT_URL}/api/v1/forms/${formId}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, form: response.data.form });
  } catch (error) {
    logger.error('Failed to get form:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get form'
    });
  }
}

/**
 * Create a new form
 */
export async function createForm(req, res) {
  try {
    const { communityId } = req.params;
    const {
      title,
      description,
      fields,
      view_visibility,
      submit_visibility,
      results_visibility,
      allow_anonymous,
      submit_once_per_user
    } = req.body;

    const response = await axios.post(`${ENGAGEMENT_URL}/api/v1/forms`, {
      community_id: communityId,
      title,
      description,
      fields,
      view_visibility: view_visibility || 'community',
      submit_visibility: submit_visibility || 'community',
      results_visibility: results_visibility || 'submitter_and_admins',
      allow_anonymous: allow_anonymous || false,
      submit_once_per_user: submit_once_per_user !== false
    }, {
      headers: { Authorization: req.headers.authorization }
    });
    res.status(201).json({ success: true, form: response.data.form });
  } catch (error) {
    logger.error('Failed to create form:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to create form'
    });
  }
}

/**
 * Delete a form
 */
export async function deleteForm(req, res) {
  try {
    const { communityId, formId } = req.params;
    await axios.delete(`${ENGAGEMENT_URL}/api/v1/forms/${formId}`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, message: 'Form deleted' });
  } catch (error) {
    logger.error('Failed to delete form:', error.message);
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to delete form'
    });
  }
}

/**
 * Get submissions for a form
 */
export async function getFormSubmissions(req, res) {
  try {
    const { communityId, formId } = req.params;
    const response = await axios.get(`${ENGAGEMENT_URL}/api/v1/forms/${formId}/submissions`, {
      params: { community_id: communityId },
      headers: { Authorization: req.headers.authorization }
    });
    res.json({ success: true, submissions: response.data.submissions || [] });
  } catch (error) {
    logger.error('Failed to get form submissions:', error.message);
    if (error.response?.status === 404) {
      return res.json({ success: true, submissions: [] });
    }
    res.status(error.response?.status || 500).json({
      success: false,
      error: error.response?.data?.error || 'Failed to get form submissions'
    });
  }
}
