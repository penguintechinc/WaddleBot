import { apiClient } from './apiClient';
import { ENDPOINTS } from '../constants/config';

class AnalyticsService {
  async getDashboardStats() {
    try {
      const response = await apiClient.get(ENDPOINTS.ANALYTICS);
      return response.data.stats || {
        totalMembers: 0,
        totalCommunities: 0,
        totalModules: 0,
        todayActivity: 0,
      };
    } catch (error) {
      console.error('Error getting dashboard stats:', error);
      throw error;
    }
  }

  async getUsageStats(timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.USAGE_STATS}?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting usage stats:', error);
      throw error;
    }
  }

  async getPerformanceMetrics(timeframe = '24h') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.PERFORMANCE}?timeframe=${timeframe}`
      );
      return response.data.metrics;
    } catch (error) {
      console.error('Error getting performance metrics:', error);
      throw error;
    }
  }

  async getCommunityAnalytics(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}?timeframe=${timeframe}`
      );
      return response.data.analytics;
    } catch (error) {
      console.error('Error getting community analytics:', error);
      throw error;
    }
  }

  async getMemberActivityStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/members?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting member activity stats:', error);
      throw error;
    }
  }

  async getModuleUsageStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/modules?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting module usage stats:', error);
      throw error;
    }
  }

  async getEngagementMetrics(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/engagement?timeframe=${timeframe}`
      );
      return response.data.metrics;
    } catch (error) {
      console.error('Error getting engagement metrics:', error);
      throw error;
    }
  }

  async getGrowthMetrics(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/growth?timeframe=${timeframe}`
      );
      return response.data.metrics;
    } catch (error) {
      console.error('Error getting growth metrics:', error);
      throw error;
    }
  }

  async getReputationStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/reputation?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting reputation stats:', error);
      throw error;
    }
  }

  async getTopMembers(communityId, metric = 'activity', limit = 10) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/top-members?metric=${metric}&limit=${limit}`
      );
      return response.data.members || [];
    } catch (error) {
      console.error('Error getting top members:', error);
      throw error;
    }
  }

  async getCommandUsage(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/commands?timeframe=${timeframe}`
      );
      return response.data.usage || [];
    } catch (error) {
      console.error('Error getting command usage:', error);
      throw error;
    }
  }

  async getTimelineData(communityId, timeframe = '30d', granularity = 'day') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/timeline?timeframe=${timeframe}&granularity=${granularity}`
      );
      return response.data.timeline || [];
    } catch (error) {
      console.error('Error getting timeline data:', error);
      throw error;
    }
  }

  async getEventStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/events?timeframe=${timeframe}`
      );
      return response.data.events || [];
    } catch (error) {
      console.error('Error getting event stats:', error);
      throw error;
    }
  }

  async getPlatformBreakdown(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/platforms?timeframe=${timeframe}`
      );
      return response.data.breakdown || [];
    } catch (error) {
      console.error('Error getting platform breakdown:', error);
      throw error;
    }
  }

  async getActivityHeatmap(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/heatmap?timeframe=${timeframe}`
      );
      return response.data.heatmap || [];
    } catch (error) {
      console.error('Error getting activity heatmap:', error);
      throw error;
    }
  }

  async getRetentionMetrics(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/retention?timeframe=${timeframe}`
      );
      return response.data.metrics;
    } catch (error) {
      console.error('Error getting retention metrics:', error);
      throw error;
    }
  }

  async getCustomReport(communityId, reportConfig) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/custom-report`,
        reportConfig
      );
      return response.data.report;
    } catch (error) {
      console.error('Error getting custom report:', error);
      throw error;
    }
  }

  async exportAnalytics(communityId, reportType, format = 'csv', timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/export?type=${reportType}&format=${format}&timeframe=${timeframe}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting analytics:', error);
      throw error;
    }
  }

  async getRealtimeStats(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/realtime`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting realtime stats:', error);
      throw error;
    }
  }

  async getComparativeAnalytics(communityId, compareWith, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/compare?with=${compareWith}&timeframe=${timeframe}`
      );
      return response.data.comparison;
    } catch (error) {
      console.error('Error getting comparative analytics:', error);
      throw error;
    }
  }

  async getPredictiveAnalytics(communityId, metric, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/predictions?metric=${metric}&timeframe=${timeframe}`
      );
      return response.data.predictions;
    } catch (error) {
      console.error('Error getting predictive analytics:', error);
      throw error;
    }
  }

  async getAnomalyDetection(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/anomalies?timeframe=${timeframe}`
      );
      return response.data.anomalies || [];
    } catch (error) {
      console.error('Error getting anomaly detection:', error);
      throw error;
    }
  }

  async getModulePerformance(communityId, moduleId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/modules/${moduleId}/performance?timeframe=${timeframe}`
      );
      return response.data.performance;
    } catch (error) {
      console.error('Error getting module performance:', error);
      throw error;
    }
  }

  async getUserJourney(communityId, userId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/users/${userId}/journey?timeframe=${timeframe}`
      );
      return response.data.journey || [];
    } catch (error) {
      console.error('Error getting user journey:', error);
      throw error;
    }
  }

  async getChannelStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/channels?timeframe=${timeframe}`
      );
      return response.data.channels || [];
    } catch (error) {
      console.error('Error getting channel stats:', error);
      throw error;
    }
  }

  async getModerationStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/moderation?timeframe=${timeframe}`
      );
      return response.data.moderation;
    } catch (error) {
      console.error('Error getting moderation stats:', error);
      throw error;
    }
  }

  async getAutomationStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/automation?timeframe=${timeframe}`
      );
      return response.data.automation;
    } catch (error) {
      console.error('Error getting automation stats:', error);
      throw error;
    }
  }

  async getIntegrationStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/integrations?timeframe=${timeframe}`
      );
      return response.data.integrations || [];
    } catch (error) {
      console.error('Error getting integration stats:', error);
      throw error;
    }
  }

  async getWebhookStats(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/webhooks?timeframe=${timeframe}`
      );
      return response.data.webhooks || [];
    } catch (error) {
      console.error('Error getting webhook stats:', error);
      throw error;
    }
  }

  async createAlert(communityId, alertConfig) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/alerts`,
        alertConfig
      );
      return response.data.alert;
    } catch (error) {
      console.error('Error creating alert:', error);
      throw error;
    }
  }

  async getAlerts(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/alerts`
      );
      return response.data.alerts || [];
    } catch (error) {
      console.error('Error getting alerts:', error);
      throw error;
    }
  }

  async updateAlert(communityId, alertId, alertConfig) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/alerts/${alertId}`,
        alertConfig
      );
      return response.data.alert;
    } catch (error) {
      console.error('Error updating alert:', error);
      throw error;
    }
  }

  async deleteAlert(communityId, alertId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/alerts/${alertId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting alert:', error);
      throw error;
    }
  }

  async getAlertHistory(communityId, alertId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/alerts/${alertId}/history`
      );
      return response.data.history || [];
    } catch (error) {
      console.error('Error getting alert history:', error);
      throw error;
    }
  }

  async subscribeToRealtimeUpdates(communityId, callback) {
    try {
      // This would typically use WebSocket or Server-Sent Events
      // For now, we'll implement a polling mechanism
      const intervalId = setInterval(async () => {
        try {
          const stats = await this.getRealtimeStats(communityId);
          callback(stats);
        } catch (error) {
          console.error('Error in realtime update:', error);
        }
      }, 5000); // Poll every 5 seconds

      return () => clearInterval(intervalId);
    } catch (error) {
      console.error('Error subscribing to realtime updates:', error);
      throw error;
    }
  }

  async generateInsights(communityId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/insights?timeframe=${timeframe}`
      );
      return response.data.insights || [];
    } catch (error) {
      console.error('Error generating insights:', error);
      throw error;
    }
  }

  async getBenchmarks(communityId, category = 'all') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_STATS.replace(':id', communityId)}/benchmarks?category=${category}`
      );
      return response.data.benchmarks;
    } catch (error) {
      console.error('Error getting benchmarks:', error);
      throw error;
    }
  }
}

export const analyticsService = new AnalyticsService();