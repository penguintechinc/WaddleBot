// Kong Gateway management controller
import kongClient from '../utils/kongClient.js';
import {
  generateSelfSignedCertificate,
  generateCertbotCertificate,
  renewCertbotCertificate,
  getCertbotCertificates
} from '../utils/certificates.js';

/**
 * Handle Kong API errors gracefully
 * Returns a standardized error response object and HTTP status code
 */
const handleKongError = (error) => {
  // Connection errors (Kong not available)
  if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND' || error.code === 'ETIMEDOUT' || !error.response) {
    return {
      status: 503,
      response: {
        success: false,
        error: 'Kong Gateway is not available',
        details: 'Kong Admin API is not reachable at the configured URL. Please verify Kong is deployed and KONG_ADMIN_URL is configured correctly.',
        kongConfigured: false
      }
    };
  }

  // Kong API errors with response
  if (error.response) {
    return {
      status: error.response.status || 500,
      response: {
        success: false,
        error: error.response.data?.message || 'Kong API error',
        details: error.response.data?.message || null,
        kongConfigured: true
      }
    };
  }

  // Generic error
  return {
    status: 500,
    response: {
      success: false,
      error: 'Failed to process request',
      details: error.message || 'Unknown error occurred',
      kongConfigured: false
    }
  };
};

/**
 * Get Kong health/availability status
 */
export const getHealth = async (req, res) => {
  try {
    const health = await kongClient.getHealth();
    res.json(health);
  } catch (error) {
    console.error('Error checking Kong health:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to check Kong health',
      configured: false
    });
  }
};

// Services
export const getServices = async (req, res) => {
  try {
    const response = await kongClient.getServices();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong services:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getService = async (req, res) => {
  try {
    const response = await kongClient.getService(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong service:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createService = async (req, res) => {
  try {
    const response = await kongClient.createService(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong service:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const updateService = async (req, res) => {
  try {
    const response = await kongClient.updateService(req.params.id, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error updating Kong service:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteService = async (req, res) => {
  try {
    await kongClient.deleteService(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong service:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Routes
export const getRoutes = async (req, res) => {
  try {
    const response = await kongClient.getRoutes();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong routes:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getRoute = async (req, res) => {
  try {
    const response = await kongClient.getRoute(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong route:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getServiceRoutes = async (req, res) => {
  try {
    const response = await kongClient.getServiceRoutes(req.params.serviceId);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching service routes:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createRoute = async (req, res) => {
  try {
    const { serviceId } = req.params;
    const response = await kongClient.createRoute(serviceId, req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong route:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const updateRoute = async (req, res) => {
  try {
    const response = await kongClient.updateRoute(req.params.id, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error updating Kong route:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteRoute = async (req, res) => {
  try {
    await kongClient.deleteRoute(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong route:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Plugins
export const getPlugins = async (req, res) => {
  try {
    const response = await kongClient.getPlugins();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong plugins:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getPlugin = async (req, res) => {
  try {
    const response = await kongClient.getPlugin(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong plugin:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createPlugin = async (req, res) => {
  try {
    const response = await kongClient.createPlugin(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong plugin:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const updatePlugin = async (req, res) => {
  try {
    const response = await kongClient.updatePlugin(req.params.id, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error updating Kong plugin:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deletePlugin = async (req, res) => {
  try {
    await kongClient.deletePlugin(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong plugin:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Consumers
export const getConsumers = async (req, res) => {
  try {
    const response = await kongClient.getConsumers();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong consumers:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getConsumer = async (req, res) => {
  try {
    const response = await kongClient.getConsumer(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong consumer:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createConsumer = async (req, res) => {
  try {
    const response = await kongClient.createConsumer(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong consumer:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteConsumer = async (req, res) => {
  try {
    await kongClient.deleteConsumer(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong consumer:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Upstreams
export const getUpstreams = async (req, res) => {
  try {
    const response = await kongClient.getUpstreams();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong upstreams:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getUpstream = async (req, res) => {
  try {
    const response = await kongClient.getUpstream(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong upstream:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createUpstream = async (req, res) => {
  try {
    const response = await kongClient.createUpstream(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong upstream:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const updateUpstream = async (req, res) => {
  try {
    const response = await kongClient.updateUpstream(req.params.id, req.body);
    res.json(response.data);
  } catch (error) {
    console.error('Error updating Kong upstream:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteUpstream = async (req, res) => {
  try {
    await kongClient.deleteUpstream(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong upstream:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Targets
export const getTargets = async (req, res) => {
  try {
    const response = await kongClient.getTargets(req.params.upstreamId);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong targets:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createTarget = async (req, res) => {
  try {
    const response = await kongClient.createTarget(req.params.upstreamId, req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong target:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteTarget = async (req, res) => {
  try {
    await kongClient.deleteTarget(req.params.upstreamId, req.params.targetId);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong target:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Certificates
export const getCertificates = async (req, res) => {
  try {
    const response = await kongClient.getCertificates();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong certificates:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const getCertificate = async (req, res) => {
  try {
    const response = await kongClient.getCertificate(req.params.id);
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong certificate:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createCertificate = async (req, res) => {
  try {
    const response = await kongClient.createCertificate(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong certificate:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteCertificate = async (req, res) => {
  try {
    await kongClient.deleteCertificate(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong certificate:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Generate self-signed certificate and upload to Kong
export const generateSelfSigned = async (req, res) => {
  try {
    const {
      commonName,
      altNames,
      validityDays,
      organization,
      country,
      tags,
      uploadToKong = true
    } = req.body;

    if (!commonName) {
      return res.status(400).json({ error: 'Common name is required' });
    }

    // Generate the certificate
    const { cert, key } = await generateSelfSignedCertificate({
      commonName,
      altNames,
      validityDays,
      organization,
      country
    });

    // Upload to Kong if requested
    let kongCertificate = null;
    if (uploadToKong) {
      const certData = {
        cert,
        key,
        tags: tags || ['self-signed', commonName]
      };

      const response = await kongClient.createCertificate(certData);
      kongCertificate = response.data;
    }

    res.status(201).json({
      success: true,
      message: 'Self-signed certificate generated successfully',
      certificate: uploadToKong ? kongCertificate : { cert, key },
      uploaded: uploadToKong
    });
  } catch (error) {
    console.error('Error generating self-signed certificate:', error);
    if (uploadToKong) {
      const { status, response: errorResponse } = handleKongError(error);
      res.status(status).json(errorResponse);
    } else {
      res.status(500).json({
        error: error.message || 'Failed to generate self-signed certificate'
      });
    }
  }
};

// Generate Let's Encrypt certificate with Certbot and upload to Kong
export const generateCertbot = async (req, res) => {
  try {
    const {
      domain,
      altDomains,
      email,
      challengeType,
      staging,
      webroot,
      dnsPlugin,
      tags,
      uploadToKong = true
    } = req.body;

    if (!domain) {
      return res.status(400).json({ error: 'Domain is required' });
    }

    if (!email) {
      return res.status(400).json({ error: 'Email is required for Let\'s Encrypt registration' });
    }

    // Generate the certificate
    const { cert, key, chain } = await generateCertbotCertificate({
      domain,
      altDomains,
      email,
      challengeType,
      staging,
      webroot,
      dnsPlugin
    });

    // Upload to Kong if requested
    let kongCertificate = null;
    if (uploadToKong) {
      const certData = {
        cert,
        key,
        tags: tags || ['letsencrypt', domain, staging ? 'staging' : 'production']
      };

      const response = await kongClient.createCertificate(certData);
      kongCertificate = response.data;
    }

    res.status(201).json({
      success: true,
      message: 'Let\'s Encrypt certificate generated successfully',
      certificate: uploadToKong ? kongCertificate : { cert, key, chain },
      uploaded: uploadToKong,
      staging
    });
  } catch (error) {
    console.error('Error generating Certbot certificate:', error);
    if (uploadToKong) {
      const { status, response: errorResponse } = handleKongError(error);
      res.status(status).json(errorResponse);
    } else {
      res.status(500).json({
        error: error.message || 'Failed to generate Let\'s Encrypt certificate'
      });
    }
  }
};

// Renew Let's Encrypt certificate
export const renewCertbot = async (req, res) => {
  try {
    const { domain } = req.params;

    if (!domain) {
      return res.status(400).json({ error: 'Domain is required' });
    }

    const result = await renewCertbotCertificate(domain);

    res.json({
      success: true,
      message: result.message,
      domain
    });
  } catch (error) {
    console.error('Error renewing Certbot certificate:', error);
    res.status(500).json({
      error: error.message || 'Failed to renew certificate'
    });
  }
};

// List Certbot certificates
export const listCertbotCertificates = async (req, res) => {
  try {
    const certificates = await getCertbotCertificates();

    res.json({
      success: true,
      data: certificates
    });
  } catch (error) {
    console.error('Error listing Certbot certificates:', error);
    res.status(500).json({
      error: error.message || 'Failed to list Certbot certificates'
    });
  }
};

// SNIs
export const getSNIs = async (req, res) => {
  try {
    const response = await kongClient.getSNIs();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong SNIs:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const createSNI = async (req, res) => {
  try {
    const response = await kongClient.createSNI(req.body);
    res.status(201).json(response.data);
  } catch (error) {
    console.error('Error creating Kong SNI:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

export const deleteSNI = async (req, res) => {
  try {
    await kongClient.deleteSNI(req.params.id);
    res.status(204).send();
  } catch (error) {
    console.error('Error deleting Kong SNI:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};

// Status
export const getStatus = async (req, res) => {
  try {
    const response = await kongClient.getStatus();
    res.json(response.data);
  } catch (error) {
    console.error('Error fetching Kong status:', error);
    const { status, response: errorResponse } = handleKongError(error);
    res.status(status).json(errorResponse);
  }
};
