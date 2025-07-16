import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Modal,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { REPUTATION_CONFIG } from '../../constants/config';
import { memberService } from '../../services/memberService';
import { 
  getReputationColor, 
  getReputationLabel, 
  getReputationDescription,
  isUserBanned,
  getReputationProgress,
  formatReputationScore 
} from '../../utils/reputationUtils';

const MemberDetailScreen = ({ navigation, route }) => {
  const { communityId, memberId } = route.params;
  const [member, setMember] = useState(null);
  const [loading, setLoading] = useState(true);
  const [banModalVisible, setBanModalVisible] = useState(false);
  const [banReason, setBanReason] = useState('');

  useEffect(() => {
    loadMemberDetails();
  }, [memberId]);

  const loadMemberDetails = async () => {
    try {
      const memberData = await memberService.getMemberDetails(communityId, memberId);
      setMember(memberData);
    } catch (error) {
      Alert.alert('Error', 'Failed to load member details');
      navigation.goBack();
    } finally {
      setLoading(false);
    }
  };

  const handleBanMember = async () => {
    try {
      await memberService.banMember(communityId, memberId, banReason || 'Banned by community manager');
      Alert.alert('Success', `Member has been banned successfully. Reputation set to ${REPUTATION_CONFIG.BAN_SCORE}.`);
      setBanModalVisible(false);
      loadMemberDetails();
    } catch (error) {
      Alert.alert('Error', 'Failed to ban member');
    }
  };

  const handleUnbanMember = async () => {
    Alert.alert(
      'Unban Member',
      `Are you sure you want to unban this member? This will restore their reputation to ${REPUTATION_CONFIG.DEFAULT_SCORE}.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unban',
          onPress: async () => {
            try {
              await memberService.unbanMember(communityId, memberId);
              Alert.alert('Success', `Member has been unbanned successfully. Reputation restored to ${REPUTATION_CONFIG.DEFAULT_SCORE}.`);
              loadMemberDetails();
            } catch (error) {
              Alert.alert('Error', 'Failed to unban member');
            }
          }
        }
      ]
    );
  };

  const handleRemoveMember = async () => {
    Alert.alert(
      'Remove Member',
      'Are you sure you want to remove this member from the community?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await memberService.removeMember(communityId, memberId);
              Alert.alert('Success', 'Member removed successfully');
              navigation.goBack();
            } catch (error) {
              Alert.alert('Error', 'Failed to remove member');
            }
          }
        }
      ]
    );
  };

  const handleChangeRole = async (newRole) => {
    try {
      await memberService.updateMemberRole(communityId, memberId, newRole);
      Alert.alert('Success', `Role changed to ${newRole}`);
      loadMemberDetails();
    } catch (error) {
      Alert.alert('Error', 'Failed to change role');
    }
  };

  const getRoleColor = (role) => {
    switch (role?.toLowerCase()) {
      case 'owner':
        return COLORS.ERROR;
      case 'admin':
        return COLORS.WARNING;
      case 'moderator':
        return COLORS.INFO;
      default:
        return COLORS.TEXT_SECONDARY;
    }
  };

  const getStatusColor = (reputationScore) => {
    if (isUserBanned(reputationScore)) {
      return COLORS.REPUTATION_BANNED;
    }
    return getReputationColor(reputationScore);
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading member details...</Text>
      </View>
    );
  }

  if (!member) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Member not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.memberAvatar}>
          <Text style={styles.memberAvatarText}>
            {member.displayName.charAt(0).toUpperCase()}
          </Text>
        </View>
        <Text style={styles.memberName}>{member.displayName}</Text>
        <Text style={styles.memberUsername}>@{member.username}</Text>
        <View style={styles.memberMeta}>
          <View style={[styles.roleTag, { backgroundColor: getRoleColor(member.role) }]}>
            <Text style={styles.roleText}>{member.role}</Text>
          </View>
          <View style={[styles.statusTag, { backgroundColor: getStatusColor(member.reputationScore) }]}>
            <Text style={styles.statusText}>
              {isUserBanned(member.reputationScore) ? 'Banned' : getReputationLabel(member.reputationScore)}
            </Text>
          </View>
        </View>
        
        {/* Reputation Score Display */}
        <View style={styles.reputationContainer}>
          <Text style={styles.reputationScore}>{formatReputationScore(member.reputationScore)}</Text>
          <Text style={styles.reputationLabel}>Reputation Score</Text>
          <View style={styles.reputationBar}>
            <View 
              style={[
                styles.reputationProgress, 
                { 
                  width: `${getReputationProgress(member.reputationScore) * 100}%`,
                  backgroundColor: getReputationColor(member.reputationScore)
                }
              ]} 
            />
          </View>
          <Text style={styles.reputationDescription}>
            {getReputationDescription(member.reputationScore)}
          </Text>
        </View>
      </View>

      <View style={styles.content}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Member Information</Text>
          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Display Name:</Text>
              <Text style={styles.infoValue}>{member.displayName}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Username:</Text>
              <Text style={styles.infoValue}>{member.username}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Email:</Text>
              <Text style={styles.infoValue}>{member.email}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Role:</Text>
              <Text style={styles.infoValue}>{member.role}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Status:</Text>
              <Text style={styles.infoValue}>
                {isUserBanned(member.reputationScore) ? 'Banned' : 'Active'}
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Reputation Score:</Text>
              <Text style={[styles.infoValue, { color: getReputationColor(member.reputationScore) }]}>
                {formatReputationScore(member.reputationScore)} ({getReputationLabel(member.reputationScore)})
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Join Date:</Text>
              <Text style={styles.infoValue}>
                {new Date(member.joinDate).toLocaleDateString()}
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Last Active:</Text>
              <Text style={styles.infoValue}>
                {new Date(member.lastActive).toLocaleDateString()}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Activity Statistics</Text>
          <View style={styles.statsCard}>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{member.reputationPoints}</Text>
              <Text style={styles.statLabel}>Reputation Points</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{member.messageCount}</Text>
              <Text style={styles.statLabel}>Messages</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statValue}>{member.activeDays}</Text>
              <Text style={styles.statLabel}>Active Days</Text>
            </View>
          </View>
        </View>

        {isUserBanned(member.reputationScore) && member.banDetails && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Ban Information</Text>
            <View style={styles.banCard}>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Reputation Score:</Text>
                <Text style={[styles.infoValue, { color: COLORS.REPUTATION_BANNED }]}>
                  {formatReputationScore(member.reputationScore)} (Banned)
                </Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Banned By:</Text>
                <Text style={styles.infoValue}>{member.banDetails.bannedBy}</Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Ban Date:</Text>
                <Text style={styles.infoValue}>
                  {new Date(member.banDetails.banDate).toLocaleDateString()}
                </Text>
              </View>
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Reason:</Text>
                <Text style={styles.infoValue}>{member.banDetails.reason}</Text>
              </View>
            </View>
          </View>
        )}

        {member.role !== 'owner' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Actions</Text>
            <View style={styles.actionsCard}>
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => handleChangeRole('admin')}
              >
                <Text style={styles.actionButtonText}>Make Admin</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => handleChangeRole('moderator')}
              >
                <Text style={styles.actionButtonText}>Make Moderator</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.actionButton}
                onPress={() => handleChangeRole('member')}
              >
                <Text style={styles.actionButtonText}>Make Member</Text>
              </TouchableOpacity>

              {isUserBanned(member.reputationScore) ? (
                <TouchableOpacity
                  style={[styles.actionButton, styles.unbanButton]}
                  onPress={handleUnbanMember}
                >
                  <Text style={styles.unbanButtonText}>Unban Member (Restore to 650)</Text>
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  style={[styles.actionButton, styles.banButton]}
                  onPress={() => setBanModalVisible(true)}
                >
                  <Text style={styles.banButtonText}>Ban Member (Set to 450)</Text>
                </TouchableOpacity>
              )}

              <TouchableOpacity
                style={[styles.actionButton, styles.removeButton]}
                onPress={handleRemoveMember}
              >
                <Text style={styles.removeButtonText}>Remove Member</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>

      <Modal
        visible={banModalVisible}
        transparent={true}
        animationType="slide"
        onRequestClose={() => setBanModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <Text style={styles.modalTitle}>Ban Member</Text>
            <Text style={styles.modalSubtitle}>
              This will set {member.displayName}'s reputation to {REPUTATION_CONFIG.BAN_SCORE} and ban them from the community, portal, and mobile app.
            </Text>
            
            <Text style={styles.inputLabel}>Reason for ban:</Text>
            <TextInput
              style={styles.banReasonInput}
              placeholder="Enter reason for ban..."
              placeholderTextColor={COLORS.TEXT_MUTED}
              value={banReason}
              onChangeText={setBanReason}
              multiline
              numberOfLines={4}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.modalCancelButton}
                onPress={() => setBanModalVisible(false)}
              >
                <Text style={styles.modalCancelText}>Cancel</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.modalBanButton}
                onPress={handleBanMember}
              >
                <Text style={styles.modalBanText}>Ban Member</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.BACKGROUND,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.BACKGROUND,
  },
  loadingText: {
    fontSize: SIZES.FONT_LARGE,
    color: COLORS.TEXT_SECONDARY,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: COLORS.BACKGROUND,
  },
  errorText: {
    fontSize: SIZES.FONT_LARGE,
    color: COLORS.ERROR,
  },
  header: {
    alignItems: 'center',
    padding: SIZES.SPACING_XLARGE,
    backgroundColor: COLORS.CARD_BACKGROUND,
    ...SHADOWS.LIGHT,
  },
  memberAvatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.SECONDARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  memberAvatarText: {
    fontSize: SIZES.FONT_HERO,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  memberName: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  memberUsername: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  memberMeta: {
    flexDirection: 'row',
    gap: SIZES.SPACING_SMALL,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  reputationContainer: {
    alignItems: 'center',
    paddingVertical: SIZES.SPACING_MEDIUM,
  },
  reputationScore: {
    fontSize: SIZES.FONT_HERO,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  reputationLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  reputationBar: {
    width: 200,
    height: 8,
    backgroundColor: COLORS.BORDER,
    borderRadius: 4,
    marginBottom: SIZES.SPACING_SMALL,
  },
  reputationProgress: {
    height: '100%',
    borderRadius: 4,
  },
  reputationDescription: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
  },
  roleTag: {
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  roleText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  statusTag: {
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  statusText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  content: {
    padding: SIZES.SCREEN_MARGIN,
  },
  section: {
    marginBottom: SIZES.SPACING_XLARGE,
  },
  sectionTitle: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  infoCard: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: SIZES.SPACING_SMALL,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  infoLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    flex: 1,
  },
  infoValue: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    flex: 1,
    textAlign: 'right',
  },
  statsCard: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    flexDirection: 'row',
    justifyContent: 'space-around',
    ...SHADOWS.LIGHT,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  statLabel: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  banCard: {
    backgroundColor: COLORS.ERROR + '10',
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    borderWidth: 1,
    borderColor: COLORS.ERROR,
  },
  actionsCard: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  actionButton: {
    paddingVertical: SIZES.SPACING_MEDIUM,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_SMALL,
    backgroundColor: COLORS.INPUT_BACKGROUND,
  },
  actionButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  banButton: {
    backgroundColor: COLORS.ERROR + '20',
  },
  banButtonText: {
    color: COLORS.ERROR,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
  unbanButton: {
    backgroundColor: COLORS.SUCCESS + '20',
  },
  unbanButtonText: {
    color: COLORS.SUCCESS,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
  removeButton: {
    backgroundColor: COLORS.ERROR + '20',
  },
  removeButtonText: {
    color: COLORS.ERROR,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: COLORS.OVERLAY,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_LARGE,
    width: '90%',
    maxWidth: 400,
    ...SHADOWS.HEAVY,
  },
  modalTitle: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  modalSubtitle: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  inputLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  banReasonInput: {
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    textAlignVertical: 'top',
    marginBottom: SIZES.SPACING_LARGE,
  },
  modalActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  modalCancelButton: {
    flex: 1,
    paddingVertical: SIZES.SPACING_MEDIUM,
    marginRight: SIZES.SPACING_SMALL,
  },
  modalCancelText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
  },
  modalBanButton: {
    flex: 1,
    backgroundColor: COLORS.ERROR,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginLeft: SIZES.SPACING_SMALL,
  },
  modalBanText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
    textAlign: 'center',
    fontWeight: FONTS.WEIGHT_BOLD,
  },
});

export default MemberDetailScreen;