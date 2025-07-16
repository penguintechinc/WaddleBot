import { apiClient } from './apiClient';
import { ENDPOINTS, RAFFLE_CONFIG, GIVEAWAY_CONFIG } from '../constants/config';

class RaffleService {
  // Raffle Management
  async getRaffles(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.status) params.append('status', options.status);
      if (options.createdBy) params.append('createdBy', options.createdBy);

      const response = await apiClient.get(
        `${ENDPOINTS.RAFFLES.replace(':id', communityId)}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting raffles:', error);
      throw error;
    }
  }

  async getRaffle(communityId, raffleId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.RAFFLES.replace(':id', communityId)}/${raffleId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting raffle:', error);
      throw error;
    }
  }

  async createRaffle(communityId, raffleData) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.RAFFLES.replace(':id', communityId),
        {
          ...raffleData,
          createdAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error creating raffle:', error);
      throw error;
    }
  }

  async updateRaffle(communityId, raffleId, raffleData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.RAFFLES.replace(':id', communityId)}/${raffleId}`,
        {
          ...raffleData,
          updatedAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating raffle:', error);
      throw error;
    }
  }

  async deleteRaffle(communityId, raffleId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.RAFFLES.replace(':id', communityId)}/${raffleId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting raffle:', error);
      throw error;
    }
  }

  // Raffle Entries
  async getRaffleEntries(communityId, raffleId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);

      const response = await apiClient.get(
        `${ENDPOINTS.RAFFLE_ENTRIES
          .replace(':id', communityId)
          .replace(':raffleId', raffleId)}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting raffle entries:', error);
      throw error;
    }
  }

  async enterRaffle(communityId, raffleId, entryData) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.RAFFLE_ENTRIES
          .replace(':id', communityId)
          .replace(':raffleId', raffleId),
        {
          ...entryData,
          enteredAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error entering raffle:', error);
      throw error;
    }
  }

  async getUserRaffleEntries(communityId, raffleId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.RAFFLE_ENTRIES
          .replace(':id', communityId)
          .replace(':raffleId', raffleId)}?memberId=${memberId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting user raffle entries:', error);
      throw error;
    }
  }

  // Raffle Winners
  async drawRaffleWinners(communityId, raffleId, winnerCount = 1) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.RAFFLE_WINNERS
          .replace(':id', communityId)
          .replace(':raffleId', raffleId),
        {
          winnerCount,
          drawnAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error drawing raffle winners:', error);
      throw error;
    }
  }

  async getRaffleWinners(communityId, raffleId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.RAFFLE_WINNERS
          .replace(':id', communityId)
          .replace(':raffleId', raffleId)
      );
      return response.data;
    } catch (error) {
      console.error('Error getting raffle winners:', error);
      throw error;
    }
  }

  // Giveaway Management
  async getGiveaways(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.status) params.append('status', options.status);
      if (options.createdBy) params.append('createdBy', options.createdBy);

      const response = await apiClient.get(
        `${ENDPOINTS.GIVEAWAYS.replace(':id', communityId)}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting giveaways:', error);
      throw error;
    }
  }

  async getGiveaway(communityId, giveawayId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.GIVEAWAYS.replace(':id', communityId)}/${giveawayId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting giveaway:', error);
      throw error;
    }
  }

  async createGiveaway(communityId, giveawayData) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.GIVEAWAYS.replace(':id', communityId),
        {
          ...giveawayData,
          createdAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error creating giveaway:', error);
      throw error;
    }
  }

  async updateGiveaway(communityId, giveawayId, giveawayData) {
    try {
      const response = await apiClient.put(
        `${ENDPOINTS.GIVEAWAYS.replace(':id', communityId)}/${giveawayId}`,
        {
          ...giveawayData,
          updatedAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating giveaway:', error);
      throw error;
    }
  }

  async deleteGiveaway(communityId, giveawayId) {
    try {
      const response = await apiClient.delete(
        `${ENDPOINTS.GIVEAWAYS.replace(':id', communityId)}/${giveawayId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error deleting giveaway:', error);
      throw error;
    }
  }

  // Giveaway Entries
  async getGiveawayEntries(communityId, giveawayId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);

      const response = await apiClient.get(
        `${ENDPOINTS.GIVEAWAY_ENTRIES
          .replace(':id', communityId)
          .replace(':giveawayId', giveawayId)}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting giveaway entries:', error);
      throw error;
    }
  }

  async enterGiveaway(communityId, giveawayId, entryData) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.GIVEAWAY_ENTRIES
          .replace(':id', communityId)
          .replace(':giveawayId', giveawayId),
        {
          ...entryData,
          enteredAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error entering giveaway:', error);
      throw error;
    }
  }

  async getUserGiveawayEntry(communityId, giveawayId, memberId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.GIVEAWAY_ENTRIES
          .replace(':id', communityId)
          .replace(':giveawayId', giveawayId)}?memberId=${memberId}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting user giveaway entry:', error);
      throw error;
    }
  }

  // Giveaway Winners
  async drawGiveawayWinners(communityId, giveawayId, winnerCount = 1) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.GIVEAWAY_WINNERS
          .replace(':id', communityId)
          .replace(':giveawayId', giveawayId),
        {
          winnerCount,
          drawnAt: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error drawing giveaway winners:', error);
      throw error;
    }
  }

  async getGiveawayWinners(communityId, giveawayId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.GIVEAWAY_WINNERS
          .replace(':id', communityId)
          .replace(':giveawayId', giveawayId)
      );
      return response.data;
    } catch (error) {
      console.error('Error getting giveaway winners:', error);
      throw error;
    }
  }

  // Validation
  validateRaffleData(raffleData) {
    const errors = [];

    if (!raffleData.title || raffleData.title.trim().length === 0) {
      errors.push('Raffle title is required');
    }

    if (!raffleData.description || raffleData.description.trim().length === 0) {
      errors.push('Raffle description is required');
    }

    if (!raffleData.entryCost || raffleData.entryCost < RAFFLE_CONFIG.MIN_COST) {
      errors.push(`Entry cost must be at least ${RAFFLE_CONFIG.MIN_COST}`);
    }

    if (raffleData.entryCost > RAFFLE_CONFIG.MAX_COST) {
      errors.push(`Entry cost cannot exceed ${RAFFLE_CONFIG.MAX_COST}`);
    }

    if (!raffleData.duration || raffleData.duration < RAFFLE_CONFIG.MIN_DURATION) {
      errors.push(`Duration must be at least ${RAFFLE_CONFIG.MIN_DURATION} seconds`);
    }

    if (raffleData.duration > RAFFLE_CONFIG.MAX_DURATION) {
      errors.push(`Duration cannot exceed ${RAFFLE_CONFIG.MAX_DURATION} seconds`);
    }

    if (!raffleData.maxEntries || raffleData.maxEntries < RAFFLE_CONFIG.MIN_ENTRIES_PER_USER) {
      errors.push(`Max entries per user must be at least ${RAFFLE_CONFIG.MIN_ENTRIES_PER_USER}`);
    }

    if (raffleData.maxEntries > RAFFLE_CONFIG.MAX_ENTRIES_PER_USER) {
      errors.push(`Max entries per user cannot exceed ${RAFFLE_CONFIG.MAX_ENTRIES_PER_USER}`);
    }

    return errors;
  }

  validateGiveawayData(giveawayData) {
    const errors = [];

    if (!giveawayData.title || giveawayData.title.trim().length === 0) {
      errors.push('Giveaway title is required');
    }

    if (!giveawayData.description || giveawayData.description.trim().length === 0) {
      errors.push('Giveaway description is required');
    }

    if (!giveawayData.entryCost || giveawayData.entryCost < GIVEAWAY_CONFIG.MIN_COST) {
      errors.push(`Entry cost must be at least ${GIVEAWAY_CONFIG.MIN_COST}`);
    }

    if (giveawayData.entryCost > GIVEAWAY_CONFIG.MAX_COST) {
      errors.push(`Entry cost cannot exceed ${GIVEAWAY_CONFIG.MAX_COST}`);
    }

    if (!giveawayData.duration || giveawayData.duration < GIVEAWAY_CONFIG.MIN_DURATION) {
      errors.push(`Duration must be at least ${GIVEAWAY_CONFIG.MIN_DURATION} seconds`);
    }

    if (giveawayData.duration > GIVEAWAY_CONFIG.MAX_DURATION) {
      errors.push(`Duration cannot exceed ${GIVEAWAY_CONFIG.MAX_DURATION} seconds`);
    }

    return errors;
  }

  // Formatting
  formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${remainingSeconds}s`;
    } else if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      return `${remainingSeconds}s`;
    }
  }

  formatTimeRemaining(endTime) {
    const now = new Date();
    const end = new Date(endTime);
    const diff = Math.max(0, end - now);

    if (diff === 0) {
      return 'Ended';
    }

    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  }

  // Status
  getRaffleStatus(raffle) {
    const now = new Date();
    const startTime = new Date(raffle.startTime);
    const endTime = new Date(raffle.endTime);

    if (now < startTime) {
      return 'scheduled';
    } else if (now >= startTime && now < endTime) {
      return 'active';
    } else if (now >= endTime && !raffle.winnersDrawn) {
      return 'ended';
    } else if (raffle.winnersDrawn) {
      return 'completed';
    } else {
      return 'cancelled';
    }
  }

  getStatusColor(status) {
    const statusColors = {
      scheduled: '#2196F3',
      active: '#4CAF50',
      ended: '#FF9800',
      completed: '#9C27B0',
      cancelled: '#757575',
    };
    return statusColors[status] || '#757575';
  }

  getStatusIcon(status) {
    const statusIcons = {
      scheduled: '⏰',
      active: '🎲',
      ended: '⏳',
      completed: '🏆',
      cancelled: '🚫',
    };
    return statusIcons[status] || '❓';
  }

  // Statistics
  async getRaffleStatistics(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.RAFFLES.replace(':id', communityId)}/statistics`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting raffle statistics:', error);
      throw error;
    }
  }

  async getGiveawayStatistics(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.GIVEAWAYS.replace(':id', communityId)}/statistics`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting giveaway statistics:', error);
      throw error;
    }
  }
}

export const raffleService = new RaffleService();