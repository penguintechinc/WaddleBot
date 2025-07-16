import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  RefreshControl,
  Alert,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { communityService } from '../../services/communityService';
import { analyticsService } from '../../services/analyticsService';

const DashboardScreen = ({ navigation }) => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [communities, setCommunities] = useState([]);
  const [stats, setStats] = useState({
    totalMembers: 0,
    totalCommunities: 0,
    totalModules: 0,
    todayActivity: 0,
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      const [communitiesData, statsData] = await Promise.all([
        communityService.getUserCommunities(),
        analyticsService.getDashboardStats(),
      ]);

      setCommunities(communitiesData);
      setStats(statsData);
    } catch (error) {
      Alert.alert('Error', 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadDashboardData();
    setRefreshing(false);
  };

  const navigateToCommunity = (community) => {
    navigation.navigate('CommunityDetail', { communityId: community.id });
  };

  const StatCard = ({ title, value, icon, color = COLORS.SECONDARY }) => (
    <View style={styles.statCard}>
      <View style={[styles.statIcon, { backgroundColor: color }]}>
        <Text style={styles.statIconText}>{icon}</Text>
      </View>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statTitle}>{title}</Text>
    </View>
  );

  const CommunityCard = ({ community }) => (
    <TouchableOpacity
      style={styles.communityCard}
      onPress={() => navigateToCommunity(community)}
    >
      <View style={styles.communityHeader}>
        <View style={styles.communityInfo}>
          <Text style={styles.communityName}>{community.name}</Text>
          <Text style={styles.communityPlatform}>{community.platform}</Text>
        </View>
        <View style={[styles.communityStatus, 
          { backgroundColor: community.isActive ? COLORS.SUCCESS : COLORS.TEXT_MUTED }]}>
          <Text style={styles.communityStatusText}>
            {community.isActive ? 'Active' : 'Inactive'}
          </Text>
        </View>
      </View>
      
      <View style={styles.communityStats}>
        <View style={styles.communityStatItem}>
          <Text style={styles.communityStatValue}>{community.memberCount}</Text>
          <Text style={styles.communityStatLabel}>Members</Text>
        </View>
        <View style={styles.communityStatItem}>
          <Text style={styles.communityStatValue}>{community.moduleCount}</Text>
          <Text style={styles.communityStatLabel}>Modules</Text>
        </View>
        <View style={styles.communityStatItem}>
          <Text style={styles.communityStatValue}>{community.dailyActivity}</Text>
          <Text style={styles.communityStatLabel}>Today</Text>
        </View>
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading dashboard...</Text>
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
      <View style={styles.header}>
        <LinearGradient
          colors={[COLORS.PRIMARY, '#333333']}
          style={styles.headerGradient}
        >
          <Text style={styles.headerTitle}>Community Dashboard</Text>
          <Text style={styles.headerSubtitle}>Manage your communities</Text>
        </LinearGradient>
      </View>

      <View style={styles.content}>
        <View style={styles.statsContainer}>
          <View style={styles.statsRow}>
            <StatCard
              title="Communities"
              value={stats.totalCommunities}
              icon="🏠"
              color={COLORS.SECONDARY}
            />
            <StatCard
              title="Members"
              value={stats.totalMembers}
              icon="👥"
              color={COLORS.INFO}
            />
          </View>
          <View style={styles.statsRow}>
            <StatCard
              title="Modules"
              value={stats.totalModules}
              icon="🔧"
              color={COLORS.SUCCESS}
            />
            <StatCard
              title="Today's Activity"
              value={stats.todayActivity}
              icon="⚡"
              color={COLORS.WARNING}
            />
          </View>
        </View>

        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Your Communities</Text>
            <TouchableOpacity
              style={styles.viewAllButton}
              onPress={() => navigation.navigate('Communities')}
            >
              <Text style={styles.viewAllText}>View All</Text>
            </TouchableOpacity>
          </View>

          {communities.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>No communities found</Text>
              <TouchableOpacity
                style={styles.addCommunityButton}
                onPress={() => navigation.navigate('AddCommunity')}
              >
                <Text style={styles.addCommunityText}>Add Community</Text>
              </TouchableOpacity>
            </View>
          ) : (
            communities.slice(0, 3).map((community) => (
              <CommunityCard key={community.id} community={community} />
            ))
          )}
        </View>

        <View style={styles.quickActions}>
          <Text style={styles.sectionTitle}>Quick Actions</Text>
          <View style={styles.actionsGrid}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => navigation.navigate('Members')}
            >
              <Text style={styles.actionIcon}>👥</Text>
              <Text style={styles.actionText}>Manage Members</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => navigation.navigate('Modules')}
            >
              <Text style={styles.actionIcon}>🔧</Text>
              <Text style={styles.actionText}>Module Store</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => navigation.navigate('Analytics')}
            >
              <Text style={styles.actionIcon}>📊</Text>
              <Text style={styles.actionText}>Analytics</Text>
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => navigation.navigate('Settings')}
            >
              <Text style={styles.actionIcon}>⚙️</Text>
              <Text style={styles.actionText}>Settings</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>
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
  header: {
    height: 120,
    overflow: 'hidden',
  },
  headerGradient: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 40,
  },
  headerTitle: {
    fontSize: SIZES.FONT_HEADER,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_LIGHT,
    marginBottom: SIZES.SPACING_TINY,
  },
  headerSubtitle: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
    opacity: 0.8,
  },
  content: {
    padding: SIZES.SCREEN_MARGIN,
  },
  statsContainer: {
    marginBottom: SIZES.SPACING_XLARGE,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    alignItems: 'center',
    marginHorizontal: SIZES.SPACING_TINY,
    ...SHADOWS.LIGHT,
  },
  statIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  statIconText: {
    fontSize: 18,
  },
  statValue: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  statTitle: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    textAlign: 'center',
  },
  section: {
    marginBottom: SIZES.SPACING_XLARGE,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  sectionTitle: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  viewAllButton: {
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
  },
  viewAllText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.SECONDARY,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  communityCard: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  communityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  communityInfo: {
    flex: 1,
  },
  communityName: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  communityPlatform: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  communityStatus: {
    paddingHorizontal: SIZES.SPACING_SMALL,
    paddingVertical: SIZES.SPACING_TINY,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  communityStatusText: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_LIGHT,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  communityStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  communityStatItem: {
    alignItems: 'center',
  },
  communityStatValue: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  communityStatLabel: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  emptyState: {
    alignItems: 'center',
    padding: SIZES.SPACING_XLARGE,
  },
  emptyStateText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  addCommunityButton: {
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_LARGE,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  addCommunityText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  quickActions: {
    marginBottom: SIZES.SPACING_XLARGE,
  },
  actionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  actionButton: {
    width: '48%',
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  actionIcon: {
    fontSize: 24,
    marginBottom: SIZES.SPACING_SMALL,
  },
  actionText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
  },
});

export default DashboardScreen;