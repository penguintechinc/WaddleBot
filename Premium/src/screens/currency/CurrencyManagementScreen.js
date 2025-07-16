import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
  Modal,
  TextInput,
  RefreshControl,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { CURRENCY_CONFIG } from '../../constants/config';
import { currencyService } from '../../services/currencyService';
import { logService } from '../../services/logService';
import { canManageCurrency } from '../../utils/permissionUtils';

const CurrencyManagementScreen = ({ navigation, route }) => {
  const { communityId } = route.params;
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [userRole, setUserRole] = useState('admin'); // This should be fetched from user context
  const [statistics, setStatistics] = useState({});
  const [leaderboard, setLeaderboard] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [currencySettings, setCurrencySettings] = useState({});
  const [selectedMember, setSelectedMember] = useState(null);
  const [adjustModalVisible, setAdjustModalVisible] = useState(false);
  const [adjustAmount, setAdjustAmount] = useState('');
  const [adjustReason, setAdjustReason] = useState('');
  const [adjustType, setAdjustType] = useState('bonus'); // 'bonus' or 'penalty'

  useEffect(() => {
    if (canManageCurrency(userRole)) {
      loadCurrencyData();
    } else {
      Alert.alert('Permission Denied', 'You do not have permission to manage currency.');
      navigation.goBack();
    }
  }, [communityId, userRole]);

  const loadCurrencyData = async () => {
    try {
      const [stats, leaderboardData, transactionsData, settings] = await Promise.all([
        currencyService.getCurrencyStatistics(communityId),
        currencyService.getCurrencyLeaderboard(communityId, { limit: 10 }),
        currencyService.getCurrencyTransactions(communityId, { limit: 20 }),
        currencyService.getCurrencySettings(communityId),
      ]);

      setStatistics(stats);
      setLeaderboard(leaderboardData.members || []);
      setTransactions(transactionsData.transactions || []);
      setCurrencySettings(settings);
    } catch (error) {
      Alert.alert('Error', 'Failed to load currency data');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadCurrencyData();
    setRefreshing(false);
  };

  const handleMemberPress = (member) => {
    setSelectedMember(member);
    setAdjustModalVisible(true);
  };

  const handleAdjustCurrency = async () => {
    if (!selectedMember) return;

    const amount = parseFloat(adjustAmount);
    if (isNaN(amount) || amount <= 0) {
      Alert.alert('Invalid Amount', 'Please enter a valid amount greater than 0.');
      return;
    }

    if (!adjustReason.trim()) {
      Alert.alert('Reason Required', 'Please provide a reason for the adjustment.');
      return;
    }

    try {
      const adjustmentAmount = adjustType === 'penalty' ? -amount : amount;
      await currencyService.updateMemberCurrencyBalance(
        communityId,
        selectedMember.id,
        adjustmentAmount,
        adjustReason,
        'manual'
      );

      // Log the adjustment
      await logService.logAction(communityId, 'currency_adjustment', {
        memberId: selectedMember.id,
        amount: adjustmentAmount,
        reason: adjustReason,
        type: adjustType,
        performedBy: userRole,
      });

      setAdjustModalVisible(false);
      setAdjustAmount('');
      setAdjustReason('');
      setAdjustType('bonus');
      setSelectedMember(null);
      
      Alert.alert('Success', 'Currency adjustment completed successfully.');
      loadCurrencyData();
    } catch (error) {
      Alert.alert('Error', 'Failed to adjust currency balance.');
    }
  };

  const formatCurrency = (amount) => {
    return currencyService.formatCurrency(amount, currencySettings.name);
  };

  const StatCard = ({ title, value, subtitle, color = COLORS.SECONDARY }) => (
    <View style={[styles.statCard, { borderLeftColor: color }]}>
      <Text style={styles.statTitle}>{title}</Text>
      <Text style={styles.statValue}>{value}</Text>
      {subtitle && <Text style={styles.statSubtitle}>{subtitle}</Text>}
    </View>
  );

  const LeaderboardItem = ({ member, index }) => (
    <TouchableOpacity
      style={styles.leaderboardItem}
      onPress={() => handleMemberPress(member)}
    >
      <View style={styles.leaderboardRank}>
        <Text style={styles.rankText}>#{index + 1}</Text>
      </View>
      <View style={styles.leaderboardInfo}>
        <Text style={styles.memberName}>{member.displayName}</Text>
        <Text style={styles.memberUsername}>@{member.username}</Text>
      </View>
      <View style={styles.leaderboardBalance}>
        <Text style={styles.balanceText}>
          {currencyService.formatCurrencyShort(member.currencyBalance)}
        </Text>
        <Text style={styles.balanceSubtext}>{currencySettings.name}</Text>
      </View>
    </TouchableOpacity>
  );

  const TransactionItem = ({ transaction }) => (
    <View style={styles.transactionItem}>
      <View style={styles.transactionIcon}>
        <Text style={styles.transactionIconText}>
          {currencyService.getTransactionIcon(transaction.type)}
        </Text>
      </View>
      <View style={styles.transactionInfo}>
        <Text style={styles.transactionMember}>{transaction.memberName}</Text>
        <Text style={styles.transactionReason}>{transaction.reason}</Text>
        <Text style={styles.transactionDate}>
          {new Date(transaction.timestamp).toLocaleDateString()}
        </Text>
      </View>
      <View style={styles.transactionAmount}>
        <Text style={[
          styles.transactionAmountText,
          { color: transaction.amount > 0 ? COLORS.SUCCESS : COLORS.ERROR }
        ]}>
          {transaction.amount > 0 ? '+' : ''}{transaction.amount}
        </Text>
      </View>
    </View>
  );

  const AdjustmentModal = () => (
    <Modal
      visible={adjustModalVisible}
      transparent={true}
      animationType="slide"
      onRequestClose={() => setAdjustModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Adjust Currency</Text>
          <Text style={styles.modalSubtitle}>
            {selectedMember?.displayName}
          </Text>
          
          <View style={styles.currentBalanceContainer}>
            <Text style={styles.currentBalanceLabel}>Current Balance:</Text>
            <Text style={styles.currentBalanceValue}>
              {formatCurrency(selectedMember?.currencyBalance || 0)}
            </Text>
          </View>

          <View style={styles.adjustmentTypeContainer}>
            <Text style={styles.inputLabel}>Adjustment Type:</Text>
            <View style={styles.typeButtons}>
              <TouchableOpacity
                style={[
                  styles.typeButton,
                  adjustType === 'bonus' && styles.typeButtonActive,
                  { backgroundColor: adjustType === 'bonus' ? COLORS.SUCCESS : COLORS.INPUT_BACKGROUND }
                ]}
                onPress={() => setAdjustType('bonus')}
              >
                <Text style={[
                  styles.typeButtonText,
                  adjustType === 'bonus' && styles.typeButtonTextActive
                ]}>
                  Bonus (+)
                </Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={[
                  styles.typeButton,
                  adjustType === 'penalty' && styles.typeButtonActive,
                  { backgroundColor: adjustType === 'penalty' ? COLORS.ERROR : COLORS.INPUT_BACKGROUND }
                ]}
                onPress={() => setAdjustType('penalty')}
              >
                <Text style={[
                  styles.typeButtonText,
                  adjustType === 'penalty' && styles.typeButtonTextActive
                ]}>
                  Penalty (-)
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Amount:</Text>
            <TextInput
              style={styles.adjustmentInput}
              value={adjustAmount}
              onChangeText={setAdjustAmount}
              placeholder="Enter amount"
              placeholderTextColor={COLORS.TEXT_MUTED}
              keyboardType="numeric"
            />
          </View>

          <View style={styles.inputContainer}>
            <Text style={styles.inputLabel}>Reason:</Text>
            <TextInput
              style={styles.reasonInput}
              value={adjustReason}
              onChangeText={setAdjustReason}
              placeholder="Enter reason for adjustment..."
              placeholderTextColor={COLORS.TEXT_MUTED}
              multiline
              numberOfLines={3}
              textAlignVertical="top"
            />
          </View>

          <View style={styles.modalActions}>
            <TouchableOpacity
              style={styles.modalCancelButton}
              onPress={() => setAdjustModalVisible(false)}
            >
              <Text style={styles.modalCancelText}>Cancel</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={[
                styles.modalSaveButton,
                { backgroundColor: adjustType === 'bonus' ? COLORS.SUCCESS : COLORS.ERROR }
              ]}
              onPress={handleAdjustCurrency}
            >
              <Text style={styles.modalSaveText}>
                {adjustType === 'bonus' ? 'Add Bonus' : 'Apply Penalty'}
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading currency data...</Text>
      </View>
    );
  }

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          colors={[COLORS.SECONDARY]}
          tintColor={COLORS.SECONDARY}
        />
      }
    >
      <View style={styles.content}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Currency Management</Text>
          <TouchableOpacity
            style={styles.settingsButton}
            onPress={() => navigation.navigate('CommunitySettings', { communityId })}
          >
            <Text style={styles.settingsButtonText}>⚙️ Settings</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Statistics</Text>
          <View style={styles.statsGrid}>
            <StatCard
              title="Total Currency"
              value={currencyService.formatCurrencyShort(statistics.totalCurrency || 0)}
              subtitle="In circulation"
              color={COLORS.PRIMARY}
            />
            <StatCard
              title="Active Members"
              value={statistics.activeMembers || 0}
              subtitle="With currency"
              color={COLORS.SUCCESS}
            />
            <StatCard
              title="Transactions"
              value={statistics.totalTransactions || 0}
              subtitle="This month"
              color={COLORS.INFO}
            />
            <StatCard
              title="Average Balance"
              value={currencyService.formatCurrencyShort(statistics.averageBalance || 0)}
              subtitle="Per member"
              color={COLORS.WARNING}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Top Members</Text>
          <View style={styles.leaderboardContainer}>
            <FlatList
              data={leaderboard}
              keyExtractor={(item) => item.id}
              renderItem={({ item, index }) => (
                <LeaderboardItem member={item} index={index} />
              )}
              scrollEnabled={false}
              showsVerticalScrollIndicator={false}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Recent Transactions</Text>
          <View style={styles.transactionContainer}>
            <FlatList
              data={transactions}
              keyExtractor={(item) => item.id}
              renderItem={({ item }) => <TransactionItem transaction={item} />}
              scrollEnabled={false}
              showsVerticalScrollIndicator={false}
            />
          </View>
        </View>
      </View>

      <AdjustmentModal />
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
  content: {
    padding: SIZES.SCREEN_MARGIN,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  headerTitle: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  settingsButton: {
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  settingsButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
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
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  statCard: {
    width: '48%',
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_MEDIUM,
    borderLeftWidth: 4,
    ...SHADOWS.LIGHT,
  },
  statTitle: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  statValue: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  statSubtitle: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
  },
  leaderboardContainer: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    ...SHADOWS.LIGHT,
  },
  leaderboardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SIZES.SPACING_MEDIUM,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  leaderboardRank: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.SECONDARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.SPACING_MEDIUM,
  },
  rankText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  leaderboardInfo: {
    flex: 1,
  },
  memberName: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  memberUsername: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  leaderboardBalance: {
    alignItems: 'flex-end',
  },
  balanceText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.SUCCESS,
  },
  balanceSubtext: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
  },
  transactionContainer: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    ...SHADOWS.LIGHT,
  },
  transactionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: SIZES.SPACING_MEDIUM,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.BORDER,
  },
  transactionIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.SPACING_MEDIUM,
  },
  transactionIconText: {
    fontSize: SIZES.FONT_MEDIUM,
  },
  transactionInfo: {
    flex: 1,
  },
  transactionMember: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  transactionReason: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  transactionDate: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
  },
  transactionAmount: {
    alignItems: 'flex-end',
  },
  transactionAmountText: {
    fontSize: SIZES.FONT_MEDIUM,
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
    marginBottom: SIZES.SPACING_TINY,
  },
  modalSubtitle: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
    marginBottom: SIZES.SPACING_LARGE,
  },
  currentBalanceContainer: {
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_LARGE,
    alignItems: 'center',
  },
  currentBalanceLabel: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  currentBalanceValue: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  adjustmentTypeContainer: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  inputLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  typeButtons: {
    flexDirection: 'row',
    gap: SIZES.SPACING_SMALL,
  },
  typeButton: {
    flex: 1,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  typeButtonActive: {
    // Active styling handled via backgroundColor prop
  },
  typeButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  typeButtonTextActive: {
    color: COLORS.TEXT_LIGHT,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
  inputContainer: {
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  adjustmentInput: {
    height: SIZES.INPUT_HEIGHT,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  reasonInput: {
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    minHeight: 80,
  },
  modalActions: {
    flexDirection: 'row',
    gap: SIZES.SPACING_MEDIUM,
    marginTop: SIZES.SPACING_LARGE,
  },
  modalCancelButton: {
    flex: 1,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
    alignItems: 'center',
  },
  modalCancelText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  modalSaveButton: {
    flex: 1,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  modalSaveText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
});

export default CurrencyManagementScreen;