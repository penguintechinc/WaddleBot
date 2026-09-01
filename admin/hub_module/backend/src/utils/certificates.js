/**
 * Certificate generation utilities
 * Provides self-signed certificate generation and Certbot ACME integration
 */
import { exec } from 'child_process';
import { promisify } from 'util';
import crypto from 'crypto';
import fs from 'fs/promises';
import path from 'path';
import { logger } from './logger.js';

const execAsync = promisify(exec);

/**
 * Generate a self-signed SSL certificate
 * @param {Object} options - Certificate options
 * @param {string} options.commonName - Common name (domain)
 * @param {string[]} options.altNames - Subject alternative names
 * @param {number} options.validityDays - Certificate validity in days (default: 365)
 * @param {string} options.organization - Organization name
 * @param {string} options.country - Country code (2 letters)
 * @returns {Promise<{cert: string, key: string}>} - PEM-encoded certificate and private key
 */
export async function generateSelfSignedCertificate(options) {
  const {
    commonName,
    altNames = [],
    validityDays = 365,
    organization = 'Waddles',
    country = 'US'
  } = options;

  if (!commonName) {
    throw new Error('Common name is required');
  }

  logger.info('Generating self-signed certificate', { commonName, altNames, validityDays });

  try {
    // Create temporary directory for certificate files
    const tmpDir = path.join('/tmp', `cert-${Date.now()}-${Math.random().toString(36).substring(7)}`);
    await fs.mkdir(tmpDir, { recursive: true });

    const keyPath = path.join(tmpDir, 'key.pem');
    const certPath = path.join(tmpDir, 'cert.pem');
    const csrPath = path.join(tmpDir, 'csr.pem');
    const configPath = path.join(tmpDir, 'openssl.cnf');

    // Generate OpenSSL configuration with SANs
    const allNames = [commonName, ...altNames];
    const sanList = allNames.map((name, idx) => `DNS.${idx + 1} = ${name}`).join('\n');

    const opensslConfig = `
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = ${country}
O = ${organization}
CN = ${commonName}

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
${sanList}
`;

    await fs.writeFile(configPath, opensslConfig);

    // Generate private key (2048-bit RSA)
    await execAsync(`openssl genrsa -out ${keyPath} 2048`);

    // Generate certificate signing request
    await execAsync(`openssl req -new -key ${keyPath} -out ${csrPath} -config ${configPath}`);

    // Generate self-signed certificate
    await execAsync(`openssl x509 -req -days ${validityDays} -in ${csrPath} -signkey ${keyPath} -out ${certPath} -extensions v3_req -extfile ${configPath}`);

    // Read the generated certificate and key
    const cert = await fs.readFile(certPath, 'utf8');
    const key = await fs.readFile(keyPath, 'utf8');

    // Clean up temporary files
    await fs.rm(tmpDir, { recursive: true, force: true });

    logger.info('Self-signed certificate generated successfully', { commonName });

    return { cert, key };
  } catch (err) {
    logger.error('Failed to generate self-signed certificate', { error: err.message, commonName });
    throw new Error(`Certificate generation failed: ${err.message}`);
  }
}

/**
 * Generate certificate using Certbot (Let's Encrypt ACME)
 * @param {Object} options - Certbot options
 * @param {string} options.domain - Primary domain
 * @param {string[]} options.altDomains - Additional domains
 * @param {string} options.email - Email for registration
 * @param {string} options.challengeType - Challenge type: 'http' or 'dns' (default: 'http')
 * @param {boolean} options.staging - Use Let's Encrypt staging (default: false)
 * @param {string} options.webroot - Webroot path for HTTP challenge
 * @param {string} options.dnsPlugin - DNS plugin for DNS challenge (e.g., 'cloudflare', 'route53')
 * @returns {Promise<{cert: string, key: string, chain: string}>} - PEM-encoded certificate, key, and chain
 */
export async function generateCertbotCertificate(options) {
  const {
    domain,
    altDomains = [],
    email,
    challengeType = 'http',
    staging = false,
    webroot = '/var/www/html',
    dnsPlugin = null
  } = options;

  if (!domain) {
    throw new Error('Domain is required');
  }

  if (!email) {
    throw new Error('Email is required for Let\'s Encrypt registration');
  }

  logger.info('Generating certificate with Certbot', { domain, altDomains, challengeType, staging });

  try {
    // Check if certbot is installed
    try {
      await execAsync('which certbot');
    } catch (err) {
      throw new Error('Certbot is not installed. Please install certbot first.');
    }

    const allDomains = [domain, ...altDomains];
    const domainArgs = allDomains.map(d => `-d ${d}`).join(' ');
    const stagingFlag = staging ? '--staging' : '';

    let challengeArgs = '';
    if (challengeType === 'http') {
      challengeArgs = `--webroot -w ${webroot}`;
    } else if (challengeType === 'dns' && dnsPlugin) {
      challengeArgs = `--dns-${dnsPlugin}`;
    } else if (challengeType === 'standalone') {
      challengeArgs = '--standalone';
    } else {
      throw new Error(`Invalid challenge type: ${challengeType}`);
    }

    // Run certbot
    const certbotCmd = `certbot certonly ${challengeArgs} ${domainArgs} --email ${email} --agree-tos --non-interactive ${stagingFlag}`;

    logger.info('Running certbot command', { command: certbotCmd.replace(email, '[REDACTED]') });

    const { stdout, stderr } = await execAsync(certbotCmd);

    if (stderr && !stderr.includes('Successfully received certificate')) {
      logger.warn('Certbot stderr output', { stderr });
    }

    // Certificate files are stored in /etc/letsencrypt/live/{domain}/
    const certDir = `/etc/letsencrypt/live/${domain}`;

    const cert = await fs.readFile(path.join(certDir, 'cert.pem'), 'utf8');
    const key = await fs.readFile(path.join(certDir, 'privkey.pem'), 'utf8');
    const chain = await fs.readFile(path.join(certDir, 'chain.pem'), 'utf8');
    const fullchain = await fs.readFile(path.join(certDir, 'fullchain.pem'), 'utf8');

    logger.info('Certbot certificate generated successfully', { domain, staging });

    return {
      cert: fullchain, // Use fullchain for compatibility
      key,
      chain
    };
  } catch (err) {
    logger.error('Failed to generate Certbot certificate', { error: err.message, domain });
    throw new Error(`Certbot certificate generation failed: ${err.message}`);
  }
}

/**
 * Renew certificate using Certbot
 * @param {string} domain - Domain to renew
 * @returns {Promise<{success: boolean, message: string}>}
 */
export async function renewCertbotCertificate(domain) {
  try {
    logger.info('Renewing Certbot certificate', { domain });

    const { stdout, stderr } = await execAsync(`certbot renew --cert-name ${domain} --non-interactive`);

    logger.info('Certbot certificate renewed', { domain, output: stdout });

    return {
      success: true,
      message: 'Certificate renewed successfully'
    };
  } catch (err) {
    logger.error('Failed to renew Certbot certificate', { error: err.message, domain });
    throw new Error(`Certificate renewal failed: ${err.message}`);
  }
}

/**
 * Get Certbot certificate status
 * @returns {Promise<Array>} - List of Certbot certificates
 */
export async function getCertbotCertificates() {
  try {
    const { stdout } = await execAsync('certbot certificates --quiet');

    // Parse certbot output
    const certificates = [];
    const certBlocks = stdout.split('Certificate Name:').filter(b => b.trim());

    for (const block of certBlocks) {
      const lines = block.split('\n');
      const cert = {
        name: lines[0].trim(),
        domains: [],
        expiry: null,
        path: null
      };

      for (const line of lines) {
        if (line.includes('Domains:')) {
          cert.domains = line.split('Domains:')[1].trim().split(' ');
        } else if (line.includes('Expiry Date:')) {
          cert.expiry = line.split('Expiry Date:')[1].trim();
        } else if (line.includes('Certificate Path:')) {
          cert.path = line.split('Certificate Path:')[1].trim();
        }
      }

      certificates.push(cert);
    }

    return certificates;
  } catch (err) {
    // Certbot not installed or no certificates
    logger.warn('Failed to get Certbot certificates', { error: err.message });
    return [];
  }
}
