import { apiClient } from './apiClient';
import { ENDPOINTS, CURRENCY_CONFIG } from '../constants/config';

class CurrencyService {
  // Currency Settings Management
  async getCurrencySettings(communityId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.CURRENCY_SETTINGS.replace(':id', communityId)
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency settings:', error);
      throw error;
    }
  }

  async updateCurrencySettings(communityId, settings) {
    try {
      const response = await apiClient.put(
        ENDPOINTS.CURRENCY_SETTINGS.replace(':id', communityId),
        settings
      );
      return response.data;
    } catch (error) {
      console.error('Error updating currency settings:', error);
      throw error;
    }
  }

  // Member Currency Management
  async getMemberCurrencyBalance(communityId, memberId) {
    try {
      const response = await apiClient.get(
        ENDPOINTS.CURRENCY_BALANCE
          .replace(':id', communityId)
          .replace(':memberId', memberId)
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency balance:', error);
      throw error;
    }
  }

  async updateMemberCurrencyBalance(communityId, memberId, amount, reason, type = 'manual') {
    try {
      const response = await apiClient.post(
        ENDPOINTS.CURRENCY_BALANCE
          .replace(':id', communityId)
          .replace(':memberId', memberId),
        {
          amount,
          reason,
          type,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error updating currency balance:', error);
      throw error;
    }
  }

  // Currency Transactions
  async getCurrencyTransactions(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.memberId) params.append('memberId', options.memberId);
      if (options.type) params.append('type', options.type);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.CURRENCY_TRANSACTIONS.replace(':id', communityId)}?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency transactions:', error);
      throw error;
    }
  }

  async getMemberCurrencyHistory(communityId, memberId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.page) params.append('page', options.page);
      if (options.limit) params.append('limit', options.limit);
      if (options.type) params.append('type', options.type);
      if (options.startDate) params.append('startDate', options.startDate);
      if (options.endDate) params.append('endDate', options.endDate);

      const response = await apiClient.get(
        `${ENDPOINTS.CURRENCY_BALANCE
          .replace(':id', communityId)
          .replace(':memberId', memberId)}/history?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency history:', error);
      throw error;
    }
  }

  // Currency Earning
  async earnCurrency(communityId, memberId, amount, source, metadata = {}) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.CURRENCY_EARN.replace(':id', communityId),
        {
          memberId,
          amount,
          source, // 'chat_message', 'event', 'bonus', etc.
          metadata,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error earning currency:', error);
      throw error;
    }
  }

  // Currency Spending
  async spendCurrency(communityId, memberId, amount, purpose, metadata = {}) {
    try {
      const response = await apiClient.post(
        ENDPOINTS.CURRENCY_SPEND.replace(':id', communityId),
        {
          memberId,
          amount,
          purpose, // 'raffle_entry', 'giveaway_entry', 'module_purchase', etc.
          metadata,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error spending currency:', error);
      throw error;
    }
  }

  // Bulk Currency Operations
  async bulkUpdateCurrency(communityId, updates) {
    try {
      const response = await apiClient.post(
        `${ENDPOINTS.CURRENCY_SETTINGS.replace(':id', communityId)}/bulk`,
        {
          updates,
          timestamp: new Date().toISOString(),
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error bulk updating currency:', error);
      throw error;
    }
  }

  // Currency Statistics
  async getCurrencyStatistics(communityId) {
    try {
      const response = await apiClient.get(
        `${ENDPOINTS.CURRENCY_SETTINGS.replace(':id', communityId)}/stats`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency statistics:', error);
      throw error;
    }
  }

  // Currency Leaderboard
  async getCurrencyLeaderboard(communityId, options = {}) {
    try {
      const params = new URLSearchParams();
      if (options.limit) params.append('limit', options.limit);
      if (options.period) params.append('period', options.period); // 'day', 'week', 'month', 'all'

      const response = await apiClient.get(
        `${ENDPOINTS.CURRENCY_SETTINGS.replace(':id', communityId)}/leaderboard?${params}`
      );
      return response.data;
    } catch (error) {
      console.error('Error getting currency leaderboard:', error);
      throw error;
    }
  }

  // Currency Validation
  validateCurrencyAmount(amount) {
    const numAmount = parseFloat(amount);
    return !isNaN(numAmount) && numAmount >= 0 && numAmount <= CURRENCY_CONFIG.MAX_BALANCE;
  }

  validateCurrencyName(name) {
    return name && name.trim().length > 0 && name.trim().length <= 50;
  }

  validateRewardAmount(amount, type) {
    const numAmount = parseFloat(amount);
    if (isNaN(numAmount) || numAmount < 0) return false;
    
    if (type === 'chat') {
      return numAmount >= CURRENCY_CONFIG.MIN_CHAT_REWARD && 
             numAmount <= CURRENCY_CONFIG.MAX_CHAT_REWARD;
    }
    
    if (type === 'event') {
      return numAmount >= CURRENCY_CONFIG.MIN_EVENT_REWARD && 
             numAmount <= CURRENCY_CONFIG.MAX_EVENT_REWARD;
    }
    
    return true;
  }

  // Currency Formatting
  formatCurrency(amount, currencyName = CURRENCY_CONFIG.DEFAULT_NAME) {
    const numAmount = parseFloat(amount) || 0;
    return `${numAmount.toLocaleString()} ${currencyName}`;
  }

  formatCurrencyShort(amount) {
    const numAmount = parseFloat(amount) || 0;
    if (numAmount >= 1000000) {
      return `${(numAmount / 1000000).toFixed(1)}M`;
    }
    if (numAmount >= 1000) {
      return `${(numAmount / 1000).toFixed(1)}K`;
    }
    return numAmount.toLocaleString();
  }

  // Currency Activity Types
  getCurrencyActivityTypes() {
    return [
      { id: 'chat_message', name: 'Chat Messages', icon: '💬' },
      { id: 'subscription', name: 'Subscriptions', icon: '⭐' },
      { id: 'follow', name: 'Follows', icon: '👥' },
      { id: 'donation', name: 'Donations', icon: '💝' },
      { id: 'raid', name: 'Raids', icon: '🚀' },
      { id: 'host', name: 'Hosts', icon: '🎯' },
      { id: 'cheer', name: 'Cheers/Bits', icon: '🎉' },
      { id: 'reaction', name: 'Reactions', icon: '😊' },
      { id: 'voice_time', name: 'Voice Time', icon: '🎤' },
      { id: 'member_join', name: 'Member Joins', icon: '👋' },
      { id: 'boost', name: 'Server Boosts', icon: '🚀' },
      { id: 'file_share', name: 'File Shares', icon: '📎' },
      { id: 'app_mention', name: 'Bot Mentions', icon: '🤖' },
    ];
  }

  // Currency Transaction Types
  getCurrencyTransactionTypes() {
    return [
      { id: 'earned', name: 'Earned', color: '#4CAF50' },
      { id: 'spent', name: 'Spent', color: '#F44336' },
      { id: 'bonus', name: 'Bonus', color: '#FF9800' },
      { id: 'penalty', name: 'Penalty', color: '#E91E63' },
      { id: 'refund', name: 'Refund', color: '#2196F3' },
      { id: 'transfer', name: 'Transfer', color: '#9C27B0' },
      { id: 'manual', name: 'Manual Adjustment', color: '#607D8B' },
    ];
  }

  getTransactionIcon(type) {
    const icons = {
      earned: '💰',
      spent: '💸',
      bonus: '🎁',
      penalty: '⚠️',
      refund: '↩️',
      transfer: '🔄',
      manual: '⚙️',
    };
    return icons[type] || '📝';
  }

  getTransactionColor(type) {
    const types = this.getCurrencyTransactionTypes();
    const transactionType = types.find(t => t.id === type);
    return transactionType ? transactionType.color : '#757575';
  }
}

export const currencyService = new CurrencyService();