import { apiClient } from './apiClient';
import { ENDPOINTS } from '../constants/config';

class MemberService {
  async getCommunityMembers(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.search) params.append('search', options.search);
      if (options.role) params.append('role', options.role);
      if (options.status) params.append('status', options.status);
      if (options.sortBy) params.append('sortBy', options.sortBy);
      if (options.sortOrder) params.append('sortOrder', options.sortOrder);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}?${params}`
      );
      return response.data.members || [];
    } catch (error) {
      console.error('Error getting community members:', error);
      throw error;
    }
  }

  async getMemberDetails(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}`
      );
      return response.data.member;
    } catch (error) {
      console.error('Error getting member details:', error);
      throw error;
    }
  }

  async addMember(communityId, memberData) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId),
        memberData
      );
      return response.data.member;
    } catch (error) {
      console.error('Error adding member:', error);
      throw error;
    }
  }

  async updateMember(communityId, memberId, memberData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}`,
        memberData
      );
      return response.data.member;
    } catch (error) {
      console.error('Error updating member:', error);
      throw error;
    }
  }

  async removeMember(communityId, memberId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error removing member:', error);
      throw error;
    }
  }

  async updateMemberRole(communityId, memberId, newRole) {
    try {
      const response = await apiClient.patch(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/role`,
        { role: newRole }
      );
      return response.data.member;
    } catch (error) {
      console.error('Error updating member role:', error);
      throw error;
    }
  }

  async banMember(communityId, memberId, reason = '') {
    try {
      // Banning sets reputation to 450
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/reputation`,
        { 
          score: 450, 
          reason: reason || 'Banned by community manager',
          action: 'ban'
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error banning member:', error);
      throw error;
    }
  }

  async unbanMember(communityId, memberId) {
    try {
      // Unbanning restores reputation to default 650
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/reputation`,
        { 
          score: 650, 
          reason: 'Unbanned by community manager',
          action: 'unban'
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error unbanning member:', error);
      throw error;
    }
  }

  async kickMember(communityId, memberId, reason = '') {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/kick`,
        { reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error kicking member:', error);
      throw error;
    }
  }

  async timeoutMember(communityId, memberId, duration, reason = '') {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/timeout`,
        { duration, reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error timing out member:', error);
      throw error;
    }
  }

  async removeTimeout(communityId, memberId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/timeout`
      );
      return response.data;
    } catch (error) {
      console.error('Error removing timeout:', error);
      throw error;
    }
  }

  async warnMember(communityId, memberId, reason) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/warn`,
        { reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error warning member:', error);
      throw error;
    }
  }

  async getMemberWarnings(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/warnings`
      );
      return response.data.warnings || [];
    } catch (error) {
      console.error('Error getting member warnings:', error);
      throw error;
    }
  }

  async removeWarning(communityId, memberId, warningId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/warnings/${warningId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error removing warning:', error);
      throw error;
    }
  }

  async getMemberActivity(communityId, memberId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.type) params.append('type', options.type);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/activity?${params}`
      );
      return response.data.activities || [];
    } catch (error) {
      console.error('Error getting member activity:', error);
      throw error;
    }
  }

  async getMemberStats(communityId, memberId, timeframe = '30d') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/stats?timeframe=${timeframe}`
      );
      return response.data.stats;
    } catch (error) {
      console.error('Error getting member stats:', error);
      throw error;
    }
  }

  async updateMemberReputation(communityId, memberId, score, reason = '') {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/reputation`,
        { score, reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating member reputation:', error);
      throw error;
    }
  }

  async adjustMemberReputation(communityId, memberId, adjustment, reason = '') {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/reputation/adjust`,
        { adjustment, reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error adjusting member reputation:', error);
      throw error;
    }
  }

  async getMemberReputation(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/reputation`
      );
      return response.data.reputation;
    } catch (error) {
      console.error('Error getting member reputation:', error);
      throw error;
    }
  }

  async inviteMembers(communityId, invitations) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/invite`,
        { invitations }
      );
      return response.data;
    } catch (error) {
      console.error('Error inviting members:', error);
      throw error;
    }
  }

  async getPendingInvitations(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/invitations`
      );
      return response.data.invitations || [];
    } catch (error) {
      console.error('Error getting pending invitations:', error);
      throw error;
    }
  }

  async cancelInvitation(communityId, invitationId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/invitations/${invitationId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error canceling invitation:', error);
      throw error;
    }
  }

  async resendInvitation(communityId, invitationId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/invitations/${invitationId}/resend`
      );
      return response.data;
    } catch (error) {
      console.error('Error resending invitation:', error);
      throw error;
    }
  }

  async getMemberPermissions(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/permissions`
      );
      return response.data.permissions || [];
    } catch (error) {
      console.error('Error getting member permissions:', error);
      throw error;
    }
  }

  async updateMemberPermissions(communityId, memberId, permissions) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/permissions`,
        { permissions }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating member permissions:', error);
      throw error;
    }
  }

  async getMemberRoles(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/roles`
      );
      return response.data.roles || [];
    } catch (error) {
      console.error('Error getting member roles:', error);
      throw error;
    }
  }

  async assignRole(communityId, memberId, roleId) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/roles`,
        { roleId }
      );
      return response.data;
    } catch (error) {
      console.error('Error assigning role:', error);
      throw error;
    }
  }

  async removeRole(communityId, memberId, roleId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/roles/${roleId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error removing role:', error);
      throw error;
    }
  }

  async getMemberNotes(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/notes`
      );
      return response.data.notes || [];
    } catch (error) {
      console.error('Error getting member notes:', error);
      throw error;
    }
  }

  async addMemberNote(communityId, memberId, note) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/notes`,
        { note }
      );
      return response.data;
    } catch (error) {
      console.error('Error adding member note:', error);
      throw error;
    }
  }

  async updateMemberNote(communityId, memberId, noteId, note) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/notes/${noteId}`,
        { note }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating member note:', error);
      throw error;
    }
  }

  async deleteMemberNote(communityId, memberId, noteId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/notes/${noteId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting member note:', error);
      throw error;
    }
  }

  async bulkUpdateMembers(communityId, memberIds, updates) {
    try {
      const response = await apiClient.patch(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/bulk`,
        { memberIds, updates }
      );
      return response.data;
    } catch (error) {
      console.error('Error bulk updating members:', error);
      throw error;
    }
  }

  async exportMembers(communityId, format = 'csv') {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/export?format=${format}`,
        { responseType: 'blob' }
      );
      return response.data;
    } catch (error) {
      console.error('Error exporting members:', error);
      throw error;
    }
  }

  async importMembers(communityId, file) {
    try {
      const response = await apiClient.uploadFile(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/import`,
        file
      );
      return response.data;
    } catch (error) {
      console.error('Error importing members:', error);
      throw error;
    }
  }

  async searchMembers(communityId, query, options = {}) {
    try {
      const params = new URLSearchParams();
      params.append('q', query);
      if (options.limit) params.append('limit', options.limit);
      if (options.includeInactive) params.append('includeInactive', options.includeInactive);

      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/search?${params}`
      );
      return response.data.members || [];
    } catch (error) {
      console.error('Error searching members:', error);
      throw error;
    }
  }

  async getMemberHistory(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/history`
      );
      return response.data.history || [];
    } catch (error) {
      console.error('Error getting member history:', error);
      throw error;
    }
  }

  async getMemberBadges(communityId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/badges`
      );
      return response.data.badges || [];
    } catch (error) {
      console.error('Error getting member badges:', error);
      throw error;
    }
  }

  async awardBadge(communityId, memberId, badgeId, reason = '') {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/badges`,
        { badgeId, reason }
      );
      return response.data;
    } catch (error) {
      console.error('Error awarding badge:', error);
      throw error;
    }
  }

  async removeBadge(communityId, memberId, badgeId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.COMMUNITY_MEMBERS.replace(':id', communityId)}/${memberId}/badges/${badgeId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error removing badge:', error);
      throw error;
    }
  }
}

export const memberService = new MemberService();