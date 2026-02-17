/**
 * Kong API Error Handler Utility
 * Provides consistent error handling for Kong Gateway operations
 */

/**
 * Extract user-friendly error message from Kong API error
 */
export const getKongErrorMessage = (error) => {
  if (!error) return 'An unknown error occurred';

  // Service unavailable (Kong not running)
  if (error.response?.status === 503) {
    return 'Kong Gateway is not available. Please verify Kong is deployed and KONG_ADMIN_URL is configured.';
  }

  // Network errors (no response from server)
  if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT') {
    return 'Cannot connect to Kong Gateway. Please verify the service is running and accessible.';
  }

  // Kong API error with detailed message
  if (error.response?.data?.error) {
    return error.response.data.error;
  }

  // Kong API error with details field
  if (error.response?.data?.details) {
    return error.response.data.details;
  }

  // Fallback to error message
  if (error.response?.data?.message) {
    return error.response.data.message;
  }

  // Generic error message
  return 'Failed to process request. Please try again.';
};

/**
 * Check if error is Kong unavailable (503)
 */
export const isKongUnavailable = (error) => {
  return error?.response?.status === 503 || !error?.response;
};

/**
 * Handle Kong API error in a component's try-catch block
 * Returns the error message to display to user
 */
export const handleKongError = (error, defaultMessage = 'Failed to complete operation') => {
  console.error('Kong API error:', error);
  return getKongErrorMessage(error) || defaultMessage;
};
