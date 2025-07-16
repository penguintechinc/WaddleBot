import { ROLE_PERMISSIONS } from '../constants/config';

export const hasPermission = (userRole, permission) => {
  const permissions = ROLE_PERMISSIONS[userRole?.toUpperCase()] || [];
  return permissions.includes(permission);
};

export const canBanMembers = (userRole) => {
  return hasPermission(userRole, 'ban_members');
};

export const canUnbanMembers = (userRole) => {
  return hasPermission(userRole, 'unban_members');
};

export const canEditReputation = (userRole) => {
  return hasPermission(userRole, 'edit_reputation');
};

export const canManageMembers = (userRole) => {
  return hasPermission(userRole, 'manage_members');
};

export const canViewLogs = (userRole) => {
  return hasPermission(userRole, 'view_logs');
};

export const canManageModules = (userRole) => {
  return hasPermission(userRole, 'manage_modules');
};

export const canManageCurrency = (userRole) => {
  return hasPermission(userRole, 'manage_currency');
};

export const canManagePayments = (userRole) => {
  return hasPermission(userRole, 'manage_payments');
};

export const canCreateRaffles = (userRole) => {
  return hasPermission(userRole, 'create_raffles');
};

export const canCreateGiveaways = (userRole) => {
  return hasPermission(userRole, 'create_giveaways');
};

export const canParticipateRaffles = (userRole) => {
  return hasPermission(userRole, 'participate_raffles');
};

export const canParticipateGiveaways = (userRole) => {
  return hasPermission(userRole, 'participate_giveaways');
};

export const isAdminOrOwner = (userRole) => {
  return userRole?.toLowerCase() === 'owner' || userRole?.toLowerCase() === 'admin';
};

export const isModerator = (userRole) => {
  return userRole?.toLowerCase() === 'moderator';
};

export const canPerformAction = (userRole, targetRole, action) => {
  const userRoleLevel = getRoleLevel(userRole);
  const targetRoleLevel = getRoleLevel(targetRole);
  
  // Users cannot perform actions on users of equal or higher role
  if (userRoleLevel <= targetRoleLevel) {
    return false;
  }
  
  return hasPermission(userRole, action);
};

const getRoleLevel = (role) => {
  switch (role?.toLowerCase()) {
    case 'owner': return 4;
    case 'admin': return 3;
    case 'moderator': return 2;
    case 'member': return 1;
    default: return 0;
  }
};

export const getPermissionMessage = (userRole, action) => {
  if (!hasPermission(userRole, action)) {
    switch (action) {
      case 'unban_members':
        return 'Only community managers and admins can unban members';
      case 'edit_reputation':
        return 'Only community managers and admins can edit reputation scores';
      case 'ban_members':
        return 'You do not have permission to ban members';
      case 'manage_members':
        return 'You do not have permission to manage members';
      case 'view_logs':
        return 'You do not have permission to view logs';
      case 'manage_currency':
        return 'Only community managers and admins can manage currency settings';
      case 'manage_payments':
        return 'Only community managers and admins can manage payment settings';
      case 'create_raffles':
        return 'You do not have permission to create raffles';
      case 'create_giveaways':
        return 'You do not have permission to create giveaways';
      case 'participate_raffles':
        return 'You do not have permission to participate in raffles';
      case 'participate_giveaways':
        return 'You do not have permission to participate in giveaways';
      default:
        return 'You do not have permission to perform this action';
    }
  }
  return null;
};

export default {
  hasPermission,
  canBanMembers,
  canUnbanMembers,
  canEditReputation,
  canManageMembers,
  canViewLogs,
  canManageModules,
  canManageCurrency,
  canManagePayments,
  canCreateRaffles,
  canCreateGiveaways,
  canParticipateRaffles,
  canParticipateGiveaways,
  isAdminOrOwner,
  isModerator,
  canPerformAction,
  getPermissionMessage,
};