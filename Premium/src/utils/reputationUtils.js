import { REPUTATION_CONFIG } from '../constants/config';
import { COLORS } from '../constants/theme';

export const getReputationColor = (score) => {
  if (score >= 750) return COLORS.REPUTATION_EXCELLENT;
  if (score >= 650) return COLORS.REPUTATION_GOOD;
  if (score >= 550) return COLORS.REPUTATION_FAIR;
  if (score >= 500) return COLORS.REPUTATION_POOR;
  return COLORS.REPUTATION_BANNED;
};

export const getReputationLabel = (score) => {
  if (score >= 750) return 'Excellent';
  if (score >= 650) return 'Good';
  if (score >= 550) return 'Fair';
  if (score >= 500) return 'Poor';
  return 'Banned';
};

export const getReputationDescription = (score) => {
  if (score >= 750) return 'Outstanding community member';
  if (score >= 650) return 'Trusted community member';
  if (score >= 550) return 'Average community standing';
  if (score >= 500) return 'Below average standing';
  return 'Banned from community';
};

export const isUserBanned = (score, communityThreshold = REPUTATION_CONFIG.MIN_AUTO_BAN_THRESHOLD) => {
  return score <= REPUTATION_CONFIG.BAN_SCORE || score < communityThreshold;
};

export const canSetReputation = (currentScore, targetScore) => {
  return targetScore >= REPUTATION_CONFIG.MIN_SCORE && targetScore <= REPUTATION_CONFIG.MAX_SCORE;
};

export const getReputationChangeImpact = (currentScore, newScore) => {
  const currentStatus = getReputationLabel(currentScore);
  const newStatus = getReputationLabel(newScore);
  
  return {
    currentStatus,
    newStatus,
    isStatusChange: currentStatus !== newStatus,
    willBeBanned: newScore <= REPUTATION_CONFIG.BAN_SCORE,
    willBeUnbanned: currentScore <= REPUTATION_CONFIG.BAN_SCORE && newScore > REPUTATION_CONFIG.BAN_SCORE,
    scoreDifference: newScore - currentScore,
  };
};

export const validateCommunityThreshold = (threshold) => {
  return threshold >= REPUTATION_CONFIG.MIN_AUTO_BAN_THRESHOLD && 
         threshold <= REPUTATION_CONFIG.MAX_AUTO_BAN_THRESHOLD;
};

export const getReputationProgress = (score) => {
  const range = REPUTATION_CONFIG.MAX_SCORE - REPUTATION_CONFIG.MIN_SCORE;
  const progress = (score - REPUTATION_CONFIG.MIN_SCORE) / range;
  return Math.max(0, Math.min(1, progress));
};

export const getNextReputationTier = (score) => {
  if (score < 500) return { tier: 'Poor', threshold: 500 };
  if (score < 550) return { tier: 'Fair', threshold: 550 };
  if (score < 650) return { tier: 'Good', threshold: 650 };
  if (score < 750) return { tier: 'Excellent', threshold: 750 };
  return null; // Already at highest tier
};

export const getReputationTrend = (reputationHistory) => {
  if (!reputationHistory || reputationHistory.length < 2) {
    return { trend: 'stable', change: 0 };
  }

  const recent = reputationHistory.slice(-5); // Last 5 entries
  const first = recent[0].score;
  const last = recent[recent.length - 1].score;
  const change = last - first;

  if (change > 10) return { trend: 'increasing', change };
  if (change < -10) return { trend: 'decreasing', change };
  return { trend: 'stable', change };
};

export const formatReputationScore = (score) => {
  return Math.round(score).toString();
};

export const getReputationIcon = (score) => {
  if (score >= 750) return '⭐';
  if (score >= 650) return '👍';
  if (score >= 550) return '👌';
  if (score >= 500) return '⚠️';
  return '🚫';
};

export const calculateReputationAfterAction = (currentScore, action) => {
  const adjustments = {
    warn: -25,
    timeout: -50,
    kick: -75,
    ban: currentScore - REPUTATION_CONFIG.BAN_SCORE, // Set to ban score
    unban: REPUTATION_CONFIG.DEFAULT_SCORE - currentScore, // Restore to default
    reward: 25,
    promote: 50,
  };

  const adjustment = adjustments[action] || 0;
  const newScore = currentScore + adjustment;
  
  return Math.max(
    REPUTATION_CONFIG.MIN_SCORE,
    Math.min(REPUTATION_CONFIG.MAX_SCORE, newScore)
  );
};

export default {
  getReputationColor,
  getReputationLabel,
  getReputationDescription,
  isUserBanned,
  canSetReputation,
  getReputationChangeImpact,
  validateCommunityThreshold,
  getReputationProgress,
  getNextReputationTier,
  getReputationTrend,
  formatReputationScore,
  getReputationIcon,
  calculateReputationAfterAction,
};