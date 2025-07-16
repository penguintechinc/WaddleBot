import { apiClient } from './apiClient';
import { ENDPOINTS } from '../constants/config';

class LogService {
  async logAction(communityId, action, data) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/logs`,
        {
          action,
          data,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error logging action:', error);
      // Don't throw error for logging failures to avoid breaking main functionality
    }
  }

  async logMemberAction(communityId, memberId, action, details) {
    return this.logAction(communityId, 'member_action', {
      memberId,
      action,
      details,
    });
  }

  async logReputationChange(communityId, memberId, oldScore, newScore, reason, performedBy) {
    return this.logAction(communityId, 'reputation_change', {
      memberId,
      oldScore,
      newScore,
      reason,
      performedBy,
      scoreDifference: newScore - oldScore,
    });
  }

  async logBanAction(communityId, memberId, reason, performedBy) {
    return this.logAction(communityId, 'member_ban', {
      memberId,
      reason,
      performedBy,
      action: 'ban',
    });
  }

  async logUnbanAction(communityId, memberId, performedBy) {
    return this.logAction(communityId, 'member_unban', {
      memberId,
      performedBy,
      action: 'unban',
    });
  }

  async logRoleChange(communityId, memberId, oldRole, newRole, performedBy) {
    return this.logAction(communityId, 'role_change', {
      memberId,
      oldRole,
      newRole,
      performedBy,
    });
  }

  async logCommunitySettingsChange(communityId, oldSettings, newSettings, performedBy) {
    return this.logAction(communityId, 'settings_change', {
      oldSettings,
      newSettings,
      performedBy,
      changes: this.getSettingsChanges(oldSettings, newSettings),
    });
  }

  async logModuleAction(communityId, moduleId, action, performedBy, details = {}) {
    return this.logAction(communityId, 'module_action', {
      moduleId,
      action,
      performedBy,
      details,
    });
  }

  async getCommunityLogs(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.action) params.append('action', options.action);
      if (options.userId) params.append('userId', options.userId);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/logs?${params}`
      );
      return response.data.logs || [];
    } catch (error) {
      console.error('Error getting community logs:', error);
      throw error;
    }
  }

  async getMemberLogs(communityId, memberId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.action) params.append('action', options.action);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/members/${memberId}/logs?${params}`
      );
      return response.data.logs || [];
    } catch (error) {
      console.error('Error getting member logs:', error);
      throw error;
    }
  }

  async getReputationHistory(communityId, memberId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.limit) params.append('limit', options.limit);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/members/${memberId}/reputation/history?${params}`
      );
      return response.data.history || [];
    } catch (error) {
      console.error('Error getting reputation history:', error);
      throw error;
    }
  }

  async exportLogs(communityId, format = 'csv', options = {}) {
    try {
      const params = new URLSearchParams();
      params.append('format', format);
      if (options.action) params.append('action', options.action);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITIES}/${communityId}/logs/export?${params}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting logs:', error);
      throw error;
    }
  }

  getSettingsChanges(oldSettings, newSettings) {
    const changes = [];
    
    Object.keys(newSettings).forEach(key => {
      if (oldSettings[key] !== newSettings[key]) {
        changes.push({
          field: key,
          oldValue: oldSettings[key],
          newValue: newSettings[key],
        });
      }
    });
    
    return changes;
  }

  formatLogAction(log) {
    switch (log.action) {
      case 'member_ban':
        return `Banned member: ${log.data.reason || 'No reason provided'}`;
      case 'member_unban':
        return 'Unbanned member';
      case 'reputation_change':
        return `Reputation changed from ${log.data.oldScore} to ${log.data.newScore} (${log.data.scoreDifference > 0 ? '+' : ''}${log.data.scoreDifference})`;
      case 'role_change':
        return `Role changed from ${log.data.oldRole} to ${log.data.newRole}`;
      case 'settings_change':
        return `Updated community settings (${log.data.changes.length} changes)`;
      case 'module_action':
        return `Module ${log.data.action}: ${log.data.moduleId}`;
      default:
        return log.action.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
  }

  formatLogDetails(log) {
    switch (log.action) {
      case 'reputation_change':
        return log.data.reason || 'No reason provided';
      case 'member_ban':
        return log.data.reason || 'No reason provided';
      case 'settings_change':
        return log.data.changes.map(change => 
          `${change.field}: ${change.oldValue} → ${change.newValue}`
        ).join(', ');
      default:
        return JSON.stringify(log.data, null, 2);
    }
  }

  getLogIcon(action) {
    switch (action) {
      case 'member_ban': return '🚫';
      case 'member_unban': return '✅';
      case 'reputation_change': return '📊';
      case 'role_change': return '👑';
      case 'settings_change': return '⚙️';
      case 'module_action': return '🔧';
      case 'member_action': return '👤';
      default: return '📝';
    }
  }

  getLogColor(action) {
    switch (action) {
      case 'member_ban': return '#F44336';
      case 'member_unban': return '#4CAF50';
      case 'reputation_change': return '#FF9800';
      case 'role_change': return '#9C27B0';
      case 'settings_change': return '#2196F3';
      case 'module_action': return '#607D8B';
      default: return '#757575';
    }
  }
}

export const logService = new LogService();