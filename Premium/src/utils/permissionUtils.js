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
  isAdminOrOwner,
  isModerator,
  canPerformAction,
  getPermissionMessage,
};