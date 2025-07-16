import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  TextInput,
  RefreshControl,
  Modal,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { REPUTATION_CONFIG } from '../../constants/config';
import { memberService } from '../../services/memberService';
import { logService } from '../../services/logService';
import { getReputationColor, getReputationLabel, isUserBanned } from '../../utils/reputationUtils';
import { canBanMembers, canUnbanMembers, canEditReputation, getPermissionMessage } from '../../utils/permissionUtils';

const MembersScreen = ({ navigation, route }) => {
  const { communityId } = route.params;
  const [members, setMembers] = useState([]);
  const [filteredMembers, setFilteredMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);
  const [actionModalVisible, setActionModalVisible] = useState(false);
  const [reputationModalVisible, setReputationModalVisible] = useState(false);
  const [newReputationScore, setNewReputationScore] = useState('');
  const [reputationReason, setReputationReason] = useState('');
  const [userRole, setUserRole] = useState('admin'); // This should be fetched from user context

  useEffect(() => {
    loadMembers();
  }, [communityId]);

  useEffect(() => {
    filterMembers();
  }, [searchText, members]);

  const loadMembers = async () => {
    try {
      const membersData = await memberService.getCommunityMembers(communityId);
      setMembers(membersData);
      setFilteredMembers(membersData);
    } catch (error) {
      Alert.alert('Error', 'Failed to load members');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadMembers();
    setRefreshing(false);
  };

  const filterMembers = () => {
    if (!searchText) {
      setFilteredMembers(members);
      return;
    }

    const filtered = members.filter(member =>
      member.displayName.toLowerCase().includes(searchText.toLowerCase()) ||
      member.username.toLowerCase().includes(searchText.toLowerCase()) ||
      member.role.toLowerCase().includes(searchText.toLowerCase())
    );
    setFilteredMembers(filtered);
  };

  const handleMemberPress = (member) => {
    setSelectedMember(member);
    setActionModalVisible(true);
  };

  const handleRemoveMember = async (member) => {
    Alert.alert(
      'Remove Member',
      `Are you sure you want to remove ${member.displayName} from the community?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await memberService.removeMember(communityId, member.id);
              setMembers(members.filter(m => m.id !== member.id));
              setActionModalVisible(false);
              Alert.alert('Success', 'Member removed successfully');
            } catch (error) {
              Alert.alert('Error', 'Failed to remove member');
            }
          }
        }
      ]
    );
  };

  const handleBanMember = async (member) => {
    if (!canBanMembers(userRole)) {
      Alert.alert('Permission Denied', getPermissionMessage(userRole, 'ban_members'));
      return;
    }

    Alert.alert(
      'Ban Member',
      `Are you sure you want to ban ${member.displayName}? This will set their reputation to ${REPUTATION_CONFIG.BAN_SCORE} and prevent them from accessing the community, portal, and app.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Ban',
          style: 'destructive',
          onPress: async () => {
            try {
              const reason = 'Banned by community manager';
              await memberService.banMember(communityId, member.id, reason);
              
              // Log the ban action
              await logService.logBanAction(communityId, member.id, reason, userRole);
              await logService.logReputationChange(
                communityId, 
                member.id, 
                member.reputationScore, 
                REPUTATION_CONFIG.BAN_SCORE, 
                reason, 
                userRole
              );
              
              const updatedMembers = members.map(m => 
                m.id === member.id ? { 
                  ...m, 
                  reputationScore: REPUTATION_CONFIG.BAN_SCORE,
                  status: 'banned'
                } : m
              );
              setMembers(updatedMembers);
              setActionModalVisible(false);
              Alert.alert('Success', `Member banned successfully. Reputation set to ${REPUTATION_CONFIG.BAN_SCORE}.`);
            } catch (error) {
              Alert.alert('Error', 'Failed to ban member');
            }
          }
        }
      ]
    );
  };

  const handleUnbanMember = async (member) => {
    if (!canUnbanMembers(userRole)) {
      Alert.alert('Permission Denied', getPermissionMessage(userRole, 'unban_members'));
      return;
    }

    Alert.alert(
      'Unban Member',
      `Are you sure you want to unban ${member.displayName}? This will restore their reputation to ${REPUTATION_CONFIG.DEFAULT_SCORE}.`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Unban',
          onPress: async () => {
            try {
              await memberService.unbanMember(communityId, member.id);
              
              // Log the unban action
              await logService.logUnbanAction(communityId, member.id, userRole);
              await logService.logReputationChange(
                communityId, 
                member.id, 
                member.reputationScore, 
                REPUTATION_CONFIG.DEFAULT_SCORE, 
                'Unbanned by community manager', 
                userRole
              );
              
              const updatedMembers = members.map(m => 
                m.id === member.id ? { 
                  ...m, 
                  reputationScore: REPUTATION_CONFIG.DEFAULT_SCORE,
                  status: 'active'
                } : m
              );
              setMembers(updatedMembers);
              setActionModalVisible(false);
              Alert.alert('Success', `Member unbanned successfully. Reputation restored to ${REPUTATION_CONFIG.DEFAULT_SCORE}.`);
            } catch (error) {
              Alert.alert('Error', 'Failed to unban member');
            }
          }
        }
      ]
    );
  };

  const handleChangeRole = async (member, newRole) => {
    try {
      const oldRole = member.role;
      await memberService.updateMemberRole(communityId, member.id, newRole);
      
      // Log the role change
      await logService.logRoleChange(communityId, member.id, oldRole, newRole, userRole);
      
      const updatedMembers = members.map(m => 
        m.id === member.id ? { ...m, role: newRole } : m
      );
      setMembers(updatedMembers);
      setActionModalVisible(false);
      Alert.alert('Success', `Role changed to ${newRole}`);
    } catch (error) {
      Alert.alert('Error', 'Failed to change role');
    }
  };

  const handleEditReputation = () => {
    if (!canEditReputation(userRole)) {
      Alert.alert('Permission Denied', getPermissionMessage(userRole, 'edit_reputation'));
      return;
    }
    
    setNewReputationScore(selectedMember.reputationScore.toString());
    setReputationReason('');
    setReputationModalVisible(true);
  };

  const handleSaveReputation = async () => {
    const score = parseInt(newReputationScore);
    
    if (isNaN(score) || score < REPUTATION_CONFIG.MIN_SCORE || score > REPUTATION_CONFIG.MAX_SCORE) {
      Alert.alert(
        'Invalid Score', 
        `Reputation score must be between ${REPUTATION_CONFIG.MIN_SCORE} and ${REPUTATION_CONFIG.MAX_SCORE}.`
      );
      return;
    }

    if (!reputationReason.trim()) {
      Alert.alert('Reason Required', 'Please provide a reason for the reputation change.');
      return;
    }

    try {
      await memberService.updateMemberReputation(communityId, selectedMember.id, score, reputationReason);
      
      // Log the reputation change
      await logService.logReputationChange(
        communityId, 
        selectedMember.id, 
        selectedMember.reputationScore, 
        score, 
        reputationReason, 
        userRole
      );
      
      const updatedMembers = members.map(m => 
        m.id === selectedMember.id ? { ...m, reputationScore: score } : m
      );
      setMembers(updatedMembers);
      setReputationModalVisible(false);
      setActionModalVisible(false);
      Alert.alert('Success', 'Reputation updated successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to update reputation');
    }
  };

  const getRoleColor = (role) => {
    switch (role.toLowerCase()) {
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

  const getStatusColor = (member) => {
    if (isUserBanned(member.reputationScore)) {
      return COLORS.REPUTATION_BANNED;
    }
    return getReputationColor(member.reputationScore);
  };

  const MemberItem = ({ member }) => (
    <TouchableOpacity
      style={styles.memberItem}
      onPress={() => handleMemberPress(member)}
    >
      <View style={styles.memberInfo}>
        <View style={styles.memberAvatar}>
          <Text style={styles.memberAvatarText}>
            {member.displayName.charAt(0).toUpperCase()}
          </Text>
        </View>
        <View style={styles.memberDetails}>
          <Text style={styles.memberName}>{member.displayName}</Text>
          <Text style={styles.memberUsername}>@{member.username}</Text>
          <Text style={styles.memberJoinDate}>
            Joined {new Date(member.joinDate).toLocaleDateString()}
          </Text>
        </View>
      </View>
      <View style={styles.memberMeta}>
        <View style={[styles.roleTag, { backgroundColor: getRoleColor(member.role) }]}>
          <Text style={styles.roleText}>{member.role}</Text>
        </View>
        <View style={[styles.statusTag, { backgroundColor: getStatusColor(member) }]}>
          <Text style={styles.statusText}>
            {isUserBanned(member.reputationScore) ? 'Banned' : getReputationLabel(member.reputationScore)}
          </Text>
        </View>
        <Text style={styles.memberPoints}>{member.reputationScore}</Text>
      </View>
    </TouchableOpacity>
  );

  const ActionModal = () => (
    <Modal
      visible={actionModalVisible}
      transparent={true}
      animationType="slide"
      onRequestClose={() => setActionModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>
            {selectedMember?.displayName}
          </Text>
          <Text style={styles.modalSubtitle}>
            @{selectedMember?.username}
          </Text>

          <View style={styles.modalActions}>
            <TouchableOpacity
              style={styles.modalAction}
              onPress={() => navigation.navigate('MemberDetail', { 
                communityId, 
                memberId: selectedMember?.id 
              })}
            >
              <Text style={styles.modalActionText}>View Details</Text>
            </TouchableOpacity>

            {selectedMember?.role !== 'owner' && (
              <>
                <TouchableOpacity
                  style={styles.modalAction}
                  onPress={() => handleChangeRole(selectedMember, 'admin')}
                >
                  <Text style={styles.modalActionText}>Make Admin</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.modalAction}
                  onPress={() => handleChangeRole(selectedMember, 'moderator')}
                >
                  <Text style={styles.modalActionText}>Make Moderator</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.modalAction}
                  onPress={() => handleChangeRole(selectedMember, 'member')}
                >
                  <Text style={styles.modalActionText}>Make Member</Text>
                </TouchableOpacity>

                {canEditReputation(userRole) && (
                  <TouchableOpacity
                    style={styles.modalAction}
                    onPress={handleEditReputation}
                  >
                    <Text style={styles.modalActionText}>Edit Reputation Score</Text>
                  </TouchableOpacity>
                )}

                {isUserBanned(selectedMember?.reputationScore) ? (
                  <TouchableOpacity
                    style={[styles.modalAction, styles.unbanAction]}
                    onPress={() => handleUnbanMember(selectedMember)}
                  >
                    <Text style={styles.unbanActionText}>Unban Member</Text>
                  </TouchableOpacity>
                ) : (
                  <TouchableOpacity
                    style={[styles.modalAction, styles.banAction]}
                    onPress={() => handleBanMember(selectedMember)}
                  >
                    <Text style={styles.banActionText}>Ban Member (Set to 450)</Text>
                  </TouchableOpacity>
                )}

                <TouchableOpacity
                  style={[styles.modalAction, styles.removeAction]}
                  onPress={() => handleRemoveMember(selectedMember)}
                >
                  <Text style={styles.removeActionText}>Remove Member</Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          <TouchableOpacity
            style={styles.modalCancel}
            onPress={() => setActionModalVisible(false)}
          >
            <Text style={styles.modalCancelText}>Cancel</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Community Members</Text>
        <TouchableOpacity
          style={styles.addButton}
          onPress={() => navigation.navigate('AddMember', { communityId })}
        >
          <Text style={styles.addButtonText}>Add Member</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search members..."
          placeholderTextColor={COLORS.TEXT_MUTED}
          value={searchText}
          onChangeText={setSearchText}
        />
      </View>

      <FlatList
        data={filteredMembers}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <MemberItem member={item} />}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[COLORS.SECONDARY]}
            tintColor={COLORS.SECONDARY}
          />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
      />

      <ActionModal />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.BACKGROUND,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: SIZES.SCREEN_MARGIN,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  headerTitle: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  addButton: {
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  addButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  searchContainer: {
    padding: SIZES.SCREEN_MARGIN,
  },
  searchInput: {
    height: SIZES.INPUT_HEIGHT,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  listContainer: {
    paddingHorizontal: SIZES.SCREEN_MARGIN,
  },
  memberItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  memberInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  memberAvatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: COLORS.SECONDARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.SPACING_MEDIUM,
  },
  memberAvatarText: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  memberDetails: {
    flex: 1,
  },
  memberName: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  memberUsername: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  memberJoinDate: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
  },
  memberMeta: {
    alignItems: 'flex-end',
  },
  roleTag: {
    paddingHorizontal: SIZES.SPACING_SMALL,
    paddingVertical: SIZES.SPACING_TINY,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_TINY,
  },
  roleText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  statusTag: {
    paddingHorizontal: SIZES.SPACING_SMALL,
    paddingVertical: SIZES.SPACING_TINY,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_TINY,
  },
  statusText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  memberPoints: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    fontWeight: FONTS.WEIGHT_MEDIUM,
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
    marginBottom: SIZES.SPACING_TINY,
  },
  modalSubtitle: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  modalActions: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  modalAction: {
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  modalActionText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
  },
  banAction: {
    backgroundColor: COLORS.ERROR + '10',
  },
  banActionText: {
    color: COLORS.ERROR,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  unbanAction: {
    backgroundColor: COLORS.SUCCESS + '10',
  },
  unbanActionText: {
    color: COLORS.SUCCESS,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  removeAction: {
    backgroundColor: COLORS.ERROR + '10',
  },
  removeActionText: {
    color: COLORS.ERROR,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  modalCancel: {
    paddingVertical: SIZES.SPACING_MEDIUM,
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
});

export default MembersScreen;