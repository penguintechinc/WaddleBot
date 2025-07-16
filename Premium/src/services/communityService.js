import { apiClient } from './apiClient';
import { ENDPOINTS } from '../constants/config';

class CommunityService {
  async getUserCommunities() {
    try {
      const response = await apiClient.get(ENDPOINTS.USER_COMMUNITIES);
      return response.data.communities || [];
    } catch (error) {
      console.error('Error getting user communities:', error);
      throw error;
    }
  }

  async getCommunityDetails(communityId) {
    try {
      const response = await apiClient.get(`${ENDPOINTS.COMMUNITIES}/${communityId}`);
      return response.data.community;
    } catch (error) {
      console.error('Error getting community details:', error);
      throw error;
    }
  }

  async createCommunity(communityData) {
    try {
      const response = await apiClient.post(ENDPOINTS.COMMUNITIES, communityData);
      return response.data.community;
    } catch (error) {
      console.error('Error creating community:', error);
      throw error;
    }
  }

  async updateCommunity(communityId, communityData) {
    try {
      const response = await apiClient.put(`${ENDPOINTS.COMMUNITIES}/${communityId}`, communityData);
      return response.data.community;
    } catch (error) {
      console.error('Error updating community:', error);
      throw error;
    }
  }

  async deleteCommunity(communityId) {
    try {
      const response = await apiClient.delete(`${ENDPOINTS.COMMUNITIES}/${communityId}`);
      return response.data;
    } catch (error) {
      console.error('Error deleting community:', error);
      throw error;
    }
  }

  async getCommunityMembers(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.search) params.append('search', options.search);
      if (options.role) params.append('role', options.role);
      if (options.status) params.append('status', options.status);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}?${params}`
      );
      return response.data.members || [];
    } catch (error) {
      console.error('Error getting community members:', error);
      throw error;
    }
  }

  async getCommunityModules(communityId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.COMMUNITY_MODULES.replace(':id', communityId)
      );
      return response.data.modules || [];
    } catch (error) {
      console.error('Error getting community modules:', error);
      throw error;
    }
  }

  async getCommunityStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting community stats:', error);
      throw error;
    }
  }

  async getCommunitySettings(communityId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.COMMUNITY_SETTINGS.replace(':id', communityId)
      );
      return response.data.settings;
    } catch (error) {
      console.error('Error getting community settings:', error);
      throw error;
    }
  }

  async updateCommunitySettings(communityId, settings) {
    try {
      const response = await apiClient.put(
        ENDPOINTS.COMMUNITY_SETTINGS.replace(':id', communityId),
        settings
      );
      return response.data.settings;
    } catch (error) {
      console.error('Error updating community settings:', error);
      throw error;
    }
  }

  async inviteMember(communityId, memberData) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/invite`,
        memberData
      );
      return response.data;
    } catch (error) {
      console.error('Error inviting member:', error);
      throw error;
    }
  }

  async transferOwnership(communityId, newOwnerId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/transfer-ownership`,
        { newOwnerId }
      );
      return response.data;
    } catch (error) {
      console.error('Error transferring ownership:', error);
      throw error;
    }
  }

  async leaveCommunity(communityId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/leave`
      );
      return response.data;
    } catch (error) {
      console.error('Error leaving community:', error);
      throw error;
    }
  }

  async getCommunityActivity(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.type) params.append('type', options.type);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/activity?${params}`
      );
      return response.data.activities || [];
    } catch (error) {
      console.error('Error getting community activity:', error);
      throw error;
    }
  }

  async getCommunityRoles(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/roles`
      );
      return response.data.roles || [];
    } catch (error) {
      console.error('Error getting community roles:', error);
      throw error;
    }
  }

  async createRole(communityId, roleData) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/roles`,
        roleData
      );
      return response.data.role;
    } catch (error) {
      console.error('Error creating role:', error);
      throw error;
    }
  }

  async updateRole(communityId, roleId, roleData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/roles/${roleId}`,
        roleData
      );
      return response.data.role;
    } catch (error) {
      console.error('Error updating role:', error);
      throw error;
    }
  }

  async deleteRole(communityId, roleId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/roles/${roleId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting role:', error);
      throw error;
    }
  }

  async getCommunityBans(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/bans`
      );
      return response.data.bans || [];
    } catch (error) {
      console.error('Error getting community bans:', error);
      throw error;
    }
  }

  async getBanDetails(communityId, banId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/bans/${banId}`
      );
      return response.data.ban;
    } catch (error) {
      console.error('Error getting ban details:', error);
      throw error;
    }
  }

  async uploadCommunityImage(communityId, imageFile) {
    try {
      const response = await apiClient.uploadCommunityImage(communityId, imageFile);
      return response.data;
    } catch (error) {
      console.error('Error uploading community image:', error);
      throw error;
    }
  }

  async getCommunityIntegrations(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/integrations`
      );
      return response.data.integrations || [];
    } catch (error) {
      console.error('Error getting community integrations:', error);
      throw error;
    }
  }

  async updateIntegration(communityId, platform, integrationData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/integrations/${platform}`,
        integrationData
      );
      return response.data.integration;
    } catch (error) {
      console.error('Error updating integration:', error);
      throw error;
    }
  }

  async enableIntegration(communityId, platform) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/integrations/${platform}/enable`
      );
      return response.data;
    } catch (error) {
      console.error('Error enabling integration:', error);
      throw error;
    }
  }

  async disableIntegration(communityId, platform) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/integrations/${platform}/disable`
      );
      return response.data;
    } catch (error) {
      console.error('Error disabling integration:', error);
      throw error;
    }
  }

  async getCommunityWebhooks(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/webhooks`
      );
      return response.data.webhooks || [];
    } catch (error) {
      console.error('Error getting community webhooks:', error);
      throw error;
    }
  }

  async createWebhook(communityId, webhookData) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/webhooks`,
        webhookData
      );
      return response.data.webhook;
    } catch (error) {
      console.error('Error creating webhook:', error);
      throw error;
    }
  }

  async updateWebhook(communityId, webhookId, webhookData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/webhooks/${webhookId}`,
        webhookData
      );
      return response.data.webhook;
    } catch (error) {
      console.error('Error updating webhook:', error);
      throw error;
    }
  }

  async deleteWebhook(communityId, webhookId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/webhooks/${webhookId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting webhook:', error);
      throw error;
    }
  }

  async testWebhook(communityId, webhookId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/webhooks/${webhookId}/test`
      );
      return response.data;
    } catch (error) {
      console.error('Error testing webhook:', error);
      throw error;
    }
  }

  async exportCommunityData(communityId, format = 'json') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/export?format=${format}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting community data:', error);
      throw error;
    }
  }

  async importCommunityData(communityId, file) {
    try {
      const response = await apiClient.uploadFile(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/import`,
        file
      );
      return response.data;
    } catch (error) {
      console.error('Error importing community data:', error);
      throw error;
    }
  }
}

export const communityService = new CommunityService();