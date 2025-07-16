import { apiClient } from './apiClient';
import { ENDPOINTS } from '../constants/config';

class ModuleService {
  async getInstalledModules(communityId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting installed modules:', error);
      throw error;
    }
  }

  async getAvailableModules(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}?communityId=${communityId}&available=true`
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting available modules:', error);
      throw error;
    }
  }

  async getModuleDetails(communityId, moduleId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/${moduleId}?communityId=${communityId}`
      );
      return response.data.module;
    } catch (error) {
      console.error('Error getting module details:', error);
      throw error;
    }
  }

  async installModule(communityId, moduleId, config = {}) {
    try {
      const response = await apiClient.post(ENDPOINTS.MODULE_INSTALL, {
        communityId,
        moduleId,
        config,
      });
      return response.data;
    } catch (error) {
      console.error('Error installing module:', error);
      throw error;
    }
  }

  async uninstallModule(communityId, moduleId) {
    try {
      const response = await apiClient.post(ENDPOINTS.MODULE_UNINSTALL, {
        communityId,
        moduleId,
      });
      return response.data;
    } catch (error) {
      console.error('Error uninstalling module:', error);
      throw error;
    }
  }

  async toggleModule(communityId, moduleId, enabled) {
    try {
      const response = await apiClient.post(ENDPOINTS.MODULE_TOGGLE, {
        communityId,
        moduleId,
        enabled,
      });
      return response.data;
    } catch (error) {
      console.error('Error toggling module:', error);
      throw error;
    }
  }

  async getModuleConfig(communityId, moduleId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/config`
      );
      return response.data.config;
    } catch (error) {
      console.error('Error getting module config:', error);
      throw error;
    }
  }

  async updateModuleConfig(communityId, moduleId, config) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/config`,
        { config }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating module config:', error);
      throw error;
    }
  }

  async getModuleStats(communityId, moduleId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/stats?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting module stats:', error);
      throw error;
    }
  }

  async getModuleLogs(communityId, moduleId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.level) params.append('level', options.level);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/logs?${params}`
      );
      return response.data.logs || [];
    } catch (error) {
      console.error('Error getting module logs:', error);
      throw error;
    }
  }

  async searchModules(query, options = {}) {
    try {
      const params = new URLSearchParams();
      params.append('q', query);
      if (options.category) params.append('category', options.category);
      if (options.author) params.append('author', options.author);
      if (options.minRating) params.append('minRating', options.minRating);
      if (options.sortBy) params.append('sortBy', options.sortBy);
      if (options.sortOrder) params.append('sortOrder', options.sortOrder);
      if (options.limit) params.append('limit', options.limit);
      if (options.offset) params.append('offset', options.offset);

      const response = await apiClient.get(`${ENDPOINTS.MODULES}/search?${params}`);
      return response.data.modules || [];
    } catch (error) {
      console.error('Error searching modules:', error);
      throw error;
    }
  }

  async getModuleCategories() {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/categories`);
      return response.data.categories || [];
    } catch (error) {
      console.error('Error getting module categories:', error);
      throw error;
    }
  }

  async getFeaturedModules(limit = 10) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/featured?limit=${limit}`);
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting featured modules:', error);
      throw error;
    }
  }

  async getPopularModules(limit = 10) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/popular?limit=${limit}`);
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting popular modules:', error);
      throw error;
    }
  }

  async getModulesByCategory(category, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.limit) params.append('limit', options.limit);
      if (options.offset) params.append('offset', options.offset);
      if (options.sortBy) params.append('sortBy', options.sortBy);
      if (options.sortOrder) params.append('sortOrder', options.sortOrder);

      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/category/${category}?${params}`
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting modules by category:', error);
      throw error;
    }
  }

  async getModulesByAuthor(author, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.limit) params.append('limit', options.limit);
      if (options.offset) params.append('offset', options.offset);

      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/author/${author}?${params}`
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting modules by author:', error);
      throw error;
    }
  }

  async getModuleReviews(moduleId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.sortBy) params.append('sortBy', options.sortBy);

      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/${moduleId}/reviews?${params}`
      );
      return response.data.reviews || [];
    } catch (error) {
      console.error('Error getting module reviews:', error);
      throw error;
    }
  }

  async submitModuleReview(moduleId, review) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.MODULES}/${moduleId}/reviews`,
        review
      );
      return response.data;
    } catch (error) {
      console.error('Error submitting module review:', error);
      throw error;
    }
  }

  async updateModuleReview(moduleId, reviewId, review) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.MODULES}/${moduleId}/reviews/${reviewId}`,
        review
      );
      return response.data;
    } catch (error) {
      console.error('Error updating module review:', error);
      throw error;
    }
  }

  async deleteModuleReview(moduleId, reviewId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.MODULES}/${moduleId}/reviews/${reviewId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting module review:', error);
      throw error;
    }
  }

  async getModuleVersions(moduleId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/${moduleId}/versions`);
      return response.data.versions || [];
    } catch (error) {
      console.error('Error getting module versions:', error);
      throw error;
    }
  }

  async updateModuleVersion(communityId, moduleId, version) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/update`,
        { version }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating module version:', error);
      throw error;
    }
  }

  async getModulePermissions(moduleId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/${moduleId}/permissions`);
      return response.data.permissions || [];
    } catch (error) {
      console.error('Error getting module permissions:', error);
      throw error;
    }
  }

  async getModuleCommands(moduleId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/${moduleId}/commands`);
      return response.data.commands || [];
    } catch (error) {
      console.error('Error getting module commands:', error);
      throw error;
    }
  }

  async testModuleConnection(communityId, moduleId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/test`
      );
      return response.data;
    } catch (error) {
      console.error('Error testing module connection:', error);
      throw error;
    }
  }

  async restartModule(communityId, moduleId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/restart`
      );
      return response.data;
    } catch (error) {
      console.error('Error restarting module:', error);
      throw error;
    }
  }

  async getModuleHealth(communityId, moduleId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/health`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting module health:', error);
      throw error;
    }
  }

  async getModuleMetrics(communityId, moduleId, timeframe = '24h') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/metrics?timeframe=${timeframe}`
      );
      return response.data.metrics;
    } catch (error) {
      console.error('Error getting module metrics:', error);
      throw error;
    }
  }

  async exportModuleData(communityId, moduleId, format = 'json') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/export?format=${format}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting module data:', error);
      throw error;
    }
  }

  async importModuleData(communityId, moduleId, file) {
    try {
      const response = await apiClient.uploadFile(
        `${ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)}/${moduleId}/import`,
        file
      );
      return response.data;
    } catch (error) {
      console.error('Error importing module data:', error);
      throw error;
    }
  }

  async getModuleDependencies(moduleId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/${moduleId}/dependencies`);
      return response.data.dependencies || [];
    } catch (error) {
      console.error('Error getting module dependencies:', error);
      throw error;
    }
  }

  async checkModuleCompatibility(communityId, moduleId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/${moduleId}/compatibility?communityId=${communityId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error checking module compatibility:', error);
      throw error;
    }
  }

  async getModuleChangelog(moduleId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/${moduleId}/changelog`);
      return response.data.changelog || [];
    } catch (error) {
      console.error('Error getting module changelog:', error);
      throw error;
    }
  }

  async reportModule(moduleId, reason, details = '') {
    try {
      const response = await apiClient.post(`${ENDPOINTS.MODULES}/${moduleId}/report`, {
        reason,
        details,
      });
      return response.data;
    } catch (error) {
      console.error('Error reporting module:', error);
      throw error;
    }
  }

  async favoriteModule(moduleId) {
    try {
      const response = await apiClient.post(`${ENDPOINTS.MODULES}/${moduleId}/favorite`);
      return response.data;
    } catch (error) {
      console.error('Error favoriting module:', error);
      throw error;
    }
  }

  async unfavoriteModule(moduleId) {
    try {
      const response = await apiClient.delete(`${ENDPOINTS.MODULES}/${moduleId}/favorite`);
      return response.data;
    } catch (error) {
      console.error('Error unfavoriting module:', error);
      throw error;
    }
  }

  async getFavoriteModules() {
    try {
      const response = await apiClient.get(`${ENDPOINTS.MODULES}/favorites`);
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting favorite modules:', error);
      throw error;
    }
  }

  async getRecommendedModules(communityId, limit = 10) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.MODULES}/recommended?communityId=${communityId}&limit=${limit}`
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting recommended modules:', error);
      throw error;
    }
  }
}

export const moduleService = new ModuleService();