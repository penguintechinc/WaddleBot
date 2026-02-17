// Kong Admin API client wrapper
import axios from 'axios';

const KONG_ADMIN_URL = process.env.KONG_ADMIN_URL || 'http://kong:8001';

class KongClient {
  constructor() {
    this.client = axios.create({
      baseURL: KONG_ADMIN_URL,
      timeout: 5000,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }

  /**
   * Check if Kong Admin API is available
   * Returns a promise that resolves to true/false, never throws
   */
  async isAvailable() {
    try {
      const response = await axios.get(`${KONG_ADMIN_URL}/status`, {
        timeout: 2000
      });
      return response.status === 200;
    } catch (error) {
      return false;
    }
  }

  /**
   * Get Kong configuration and availability status
   */
  async getHealth() {
    const isAvailable = await this.isAvailable();
    return {
      configured: !!KONG_ADMIN_URL,
      available: isAvailable,
      url: KONG_ADMIN_URL
    };
  }

  // Services
  async getServices() { return this.client.get('/services'); }
  async getService(id) { return this.client.get(`/services/${id}`); }
  async createService(data) { return this.client.post('/services', data); }
  async updateService(id, data) { return this.client.patch(`/services/${id}`, data); }
  async deleteService(id) { return this.client.delete(`/services/${id}`); }

  // Routes
  async getRoutes() { return this.client.get('/routes'); }
  async getRoute(id) { return this.client.get(`/routes/${id}`); }
  async getServiceRoutes(serviceId) { return this.client.get(`/services/${serviceId}/routes`); }
  async createRoute(serviceId, data) { return this.client.post(`/services/${serviceId}/routes`, data); }
  async updateRoute(id, data) { return this.client.patch(`/routes/${id}`, data); }
  async deleteRoute(id) { return this.client.delete(`/routes/${id}`); }

  // Plugins
  async getPlugins() { return this.client.get('/plugins'); }
  async getPlugin(id) { return this.client.get(`/plugins/${id}`); }
  async createPlugin(data) { return this.client.post('/plugins', data); }
  async updatePlugin(id, data) { return this.client.patch(`/plugins/${id}`, data); }
  async deletePlugin(id) { return this.client.delete(`/plugins/${id}`); }

  // Consumers
  async getConsumers() { return this.client.get('/consumers'); }
  async getConsumer(id) { return this.client.get(`/consumers/${id}`); }
  async createConsumer(data) { return this.client.post('/consumers', data); }
  async deleteConsumer(id) { return this.client.delete(`/consumers/${id}`); }

  // Upstreams
  async getUpstreams() { return this.client.get('/upstreams'); }
  async getUpstream(id) { return this.client.get(`/upstreams/${id}`); }
  async createUpstream(data) { return this.client.post('/upstreams', data); }
  async updateUpstream(id, data) { return this.client.patch(`/upstreams/${id}`, data); }
  async deleteUpstream(id) { return this.client.delete(`/upstreams/${id}`); }

  // Targets (upstream targets)
  async getTargets(upstreamId) { return this.client.get(`/upstreams/${upstreamId}/targets`); }
  async createTarget(upstreamId, data) { return this.client.post(`/upstreams/${upstreamId}/targets`, data); }
  async deleteTarget(upstreamId, targetId) { return this.client.delete(`/upstreams/${upstreamId}/targets/${targetId}`); }

  // Certificates
  async getCertificates() { return this.client.get('/certificates'); }
  async getCertificate(id) { return this.client.get(`/certificates/${id}`); }
  async createCertificate(data) { return this.client.post('/certificates', data); }
  async deleteCertificate(id) { return this.client.delete(`/certificates/${id}`); }

  // SNIs (Server Name Indication for certificates)
  async getSNIs() { return this.client.get('/snis'); }
  async createSNI(data) { return this.client.post('/snis', data); }
  async deleteSNI(id) { return this.client.delete(`/snis/${id}`); }

  // Status
  async getStatus() { return this.client.get('/status'); }
}

export default new KongClient();
