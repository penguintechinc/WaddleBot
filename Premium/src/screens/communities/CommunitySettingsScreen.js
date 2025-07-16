import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  TextInput,
  Switch,
  Slider,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { REPUTATION_CONFIG, CURRENCY_CONFIG } from '../../constants/config';
import { communityService } from '../../services/communityService';
import { currencyService } from '../../services/currencyService';
import { validateCommunityThreshold, getReputationLabel } from '../../utils/reputationUtils';
import { canManageCurrency } from '../../utils/permissionUtils';

const CommunitySettingsScreen = ({ navigation, route }) => {
  const { communityId } = route.params;
  const [settings, setSettings] = useState({
    autoBanThreshold: REPUTATION_CONFIG.DEFAULT_AUTO_BAN_THRESHOLD,
    autoBanEnabled: true,
    name: '',
    description: '',
    isPublic: true,
    // Currency settings
    currencyEnabled: true,
    currencyName: CURRENCY_CONFIG.DEFAULT_NAME,
    chatMessageReward: CURRENCY_CONFIG.DEFAULT_CHAT_REWARD,
    eventReward: CURRENCY_CONFIG.DEFAULT_EVENT_REWARD,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [userRole, setUserRole] = useState('admin'); // This should be fetched from user context

  useEffect(() => {
    loadCommunitySettings();
  }, [communityId]);

  const loadCommunitySettings = async () => {
    try {
      const communitySettings = await communityService.getCommunitySettings(communityId);
      
      // Load currency settings if user has permission
      let currencySettings = {};
      if (canManageCurrency(userRole)) {
        try {
          currencySettings = await currencyService.getCurrencySettings(communityId);
        } catch (error) {
          console.log('Currency settings not found, using defaults');
        }
      }
      
      setSettings({
        autoBanThreshold: communitySettings.autoBanThreshold || REPUTATION_CONFIG.DEFAULT_AUTO_BAN_THRESHOLD,
        autoBanEnabled: communitySettings.autoBanEnabled !== false,
        name: communitySettings.name || '',
        description: communitySettings.description || '',
        isPublic: communitySettings.isPublic !== false,
        // Currency settings
        currencyEnabled: currencySettings.enabled !== false,
        currencyName: currencySettings.name || CURRENCY_CONFIG.DEFAULT_NAME,
        chatMessageReward: currencySettings.chatMessageReward || CURRENCY_CONFIG.DEFAULT_CHAT_REWARD,
        eventReward: currencySettings.eventReward || CURRENCY_CONFIG.DEFAULT_EVENT_REWARD,
      });
    } catch (error) {
      Alert.alert('Error', 'Failed to load community settings');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveSettings = async () => {
    if (!validateCommunityThreshold(settings.autoBanThreshold)) {
      Alert.alert(
        'Invalid Threshold',
        `Auto-ban threshold must be between ${REPUTATION_CONFIG.MIN_AUTO_BAN_THRESHOLD} and ${REPUTATION_CONFIG.MAX_AUTO_BAN_THRESHOLD}.`
      );
      return;
    }

    if (!currencyService.validateCurrencyName(settings.currencyName)) {
      Alert.alert('Invalid Currency Name', 'Currency name must be between 1 and 50 characters.');
      return;
    }

    if (!currencyService.validateRewardAmount(settings.chatMessageReward, 'chat')) {
      Alert.alert(
        'Invalid Chat Reward',
        `Chat message reward must be between ${CURRENCY_CONFIG.MIN_CHAT_REWARD} and ${CURRENCY_CONFIG.MAX_CHAT_REWARD}.`
      );
      return;
    }

    if (!currencyService.validateRewardAmount(settings.eventReward, 'event')) {
      Alert.alert(
        'Invalid Event Reward',
        `Event reward must be between ${CURRENCY_CONFIG.MIN_EVENT_REWARD} and ${CURRENCY_CONFIG.MAX_EVENT_REWARD}.`
      );
      return;
    }

    setSaving(true);
    try {
      // Save community settings
      const communitySettings = {
        autoBanThreshold: settings.autoBanThreshold,
        autoBanEnabled: settings.autoBanEnabled,
        name: settings.name,
        description: settings.description,
        isPublic: settings.isPublic,
      };
      await communityService.updateCommunitySettings(communityId, communitySettings);

      // Save currency settings if user has permission
      if (canManageCurrency(userRole)) {
        const currencySettings = {
          enabled: settings.currencyEnabled,
          name: settings.currencyName,
          chatMessageReward: settings.chatMessageReward,
          eventReward: settings.eventReward,
        };
        await currencyService.updateCurrencySettings(communityId, currencySettings);
      }

      Alert.alert('Success', 'Community settings updated successfully');
      navigation.goBack();
    } catch (error) {
      Alert.alert('Error', 'Failed to update community settings');
    } finally {
      setSaving(false);
    }
  };

  const handleThresholdChange = (value) => {
    const threshold = Math.round(value);
    setSettings(prev => ({ ...prev, autoBanThreshold: threshold }));
  };

  const getThresholdColor = (threshold) => {
    if (threshold <= 500) return COLORS.REPUTATION_BANNED;
    if (threshold <= 550) return COLORS.REPUTATION_POOR;
    if (threshold <= 650) return COLORS.REPUTATION_FAIR;
    return COLORS.REPUTATION_GOOD;
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading settings...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.content}>
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Basic Information</Text>
          <View style={styles.card}>
            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Community Name</Text>
              <TextInput
                style={styles.input}
                value={settings.name}
                onChangeText={(text) => setSettings(prev => ({ ...prev, name: text }))}
                placeholder="Enter community name"
                placeholderTextColor={COLORS.TEXT_MUTED}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.inputLabel}>Description</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={settings.description}
                onChangeText={(text) => setSettings(prev => ({ ...prev, description: text }))}
                placeholder="Enter community description"
                placeholderTextColor={COLORS.TEXT_MUTED}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
              />
            </View>

            <View style={styles.switchContainer}>
              <Text style={styles.switchLabel}>Public Community</Text>
              <Switch
                value={settings.isPublic}
                onValueChange={(value) => setSettings(prev => ({ ...prev, isPublic: value }))}
                trackColor={{ false: COLORS.BORDER, true: COLORS.SECONDARY }}
                thumbColor={settings.isPublic ? COLORS.PRIMARY : COLORS.TEXT_MUTED}
              />
            </View>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Reputation Management</Text>
          <View style={styles.card}>
            <View style={styles.switchContainer}>
              <View style={styles.switchInfo}>
                <Text style={styles.switchLabel}>Auto-Ban System</Text>
                <Text style={styles.switchDescription}>
                  Automatically ban users when their reputation falls below the threshold
                </Text>
              </View>
              <Switch
                value={settings.autoBanEnabled}
                onValueChange={(value) => setSettings(prev => ({ ...prev, autoBanEnabled: value }))}
                trackColor={{ false: COLORS.BORDER, true: COLORS.SECONDARY }}
                thumbColor={settings.autoBanEnabled ? COLORS.PRIMARY : COLORS.TEXT_MUTED}
              />
            </View>

            {settings.autoBanEnabled && (
              <>
                <View style={styles.thresholdContainer}>
                  <Text style={styles.inputLabel}>Auto-Ban Threshold</Text>
                  <Text style={styles.thresholdDescription}>
                    Users with reputation below this score will be automatically banned
                  </Text>
                  
                  <View style={styles.thresholdDisplay}>
                    <Text style={[styles.thresholdValue, { color: getThresholdColor(settings.autoBanThreshold) }]}>
                      {settings.autoBanThreshold}
                    </Text>
                    <Text style={styles.thresholdLabel}>
                      ({getReputationLabel(settings.autoBanThreshold - 1)} or below)
                    </Text>
                  </View>

                  <Slider
                    style={styles.slider}
                    minimumValue={REPUTATION_CONFIG.MIN_AUTO_BAN_THRESHOLD}
                    maximumValue={REPUTATION_CONFIG.MAX_AUTO_BAN_THRESHOLD}
                    value={settings.autoBanThreshold}
                    onValueChange={handleThresholdChange}
                    step={1}
                    minimumTrackTintColor={getThresholdColor(settings.autoBanThreshold)}
                    maximumTrackTintColor={COLORS.BORDER}
                    thumbStyle={{ backgroundColor: getThresholdColor(settings.autoBanThreshold) }}
                  />

                  <View style={styles.sliderLabels}>
                    <Text style={styles.sliderLabel}>
                      {REPUTATION_CONFIG.MIN_AUTO_BAN_THRESHOLD} (Strictest)
                    </Text>
                    <Text style={styles.sliderLabel}>
                      {REPUTATION_CONFIG.MAX_AUTO_BAN_THRESHOLD} (Most Lenient)
                    </Text>
                  </View>
                </View>

                <View style={styles.thresholdInfo}>
                  <Text style={styles.infoTitle}>Reputation Score Ranges:</Text>
                  <View style={styles.scoreRange}>
                    <View style={[styles.scoreIndicator, { backgroundColor: COLORS.REPUTATION_EXCELLENT }]} />
                    <Text style={styles.scoreText}>750-850: Excellent</Text>
                  </View>
                  <View style={styles.scoreRange}>
                    <View style={[styles.scoreIndicator, { backgroundColor: COLORS.REPUTATION_GOOD }]} />
                    <Text style={styles.scoreText}>650-749: Good</Text>
                  </View>
                  <View style={styles.scoreRange}>
                    <View style={[styles.scoreIndicator, { backgroundColor: COLORS.REPUTATION_FAIR }]} />
                    <Text style={styles.scoreText}>550-649: Fair</Text>
                  </View>
                  <View style={styles.scoreRange}>
                    <View style={[styles.scoreIndicator, { backgroundColor: COLORS.REPUTATION_POOR }]} />
                    <Text style={styles.scoreText}>500-549: Poor</Text>
                  </View>
                  <View style={styles.scoreRange}>
                    <View style={[styles.scoreIndicator, { backgroundColor: COLORS.REPUTATION_BANNED }]} />
                    <Text style={styles.scoreText}>450-499: Banned</Text>
                  </View>
                </View>
              </>
            )}
          </View>
        </View>

        {canManageCurrency(userRole) && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Currency System</Text>
            <View style={styles.card}>
              <View style={styles.switchContainer}>
                <View style={styles.switchInfo}>
                  <Text style={styles.switchLabel}>Enable Currency System</Text>
                  <Text style={styles.switchDescription}>
                    Allow members to earn and spend community currency
                  </Text>
                </View>
                <Switch
                  value={settings.currencyEnabled}
                  onValueChange={(value) => setSettings(prev => ({ ...prev, currencyEnabled: value }))}
                  trackColor={{ false: COLORS.BORDER, true: COLORS.SECONDARY }}
                  thumbColor={settings.currencyEnabled ? COLORS.PRIMARY : COLORS.TEXT_MUTED}
                />
              </View>

              {settings.currencyEnabled && (
                <>
                  <View style={styles.inputContainer}>
                    <Text style={styles.inputLabel}>Currency Name</Text>
                    <TextInput
                      style={styles.input}
                      value={settings.currencyName}
                      onChangeText={(text) => setSettings(prev => ({ ...prev, currencyName: text }))}
                      placeholder="Enter currency name (e.g., Credits, Points, Coins)"
                      placeholderTextColor={COLORS.TEXT_MUTED}
                      maxLength={50}
                    />
                  </View>

                  <View style={styles.rewardContainer}>
                    <Text style={styles.inputLabel}>Chat Message Reward</Text>
                    <Text style={styles.rewardDescription}>
                      Amount of {settings.currencyName} earned per chat message (without commands)
                    </Text>
                    <View style={styles.rewardInputContainer}>
                      <TextInput
                        style={styles.rewardInput}
                        value={settings.chatMessageReward.toString()}
                        onChangeText={(text) => {
                          const value = parseInt(text) || 0;
                          setSettings(prev => ({ ...prev, chatMessageReward: value }));
                        }}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor={COLORS.TEXT_MUTED}
                      />
                      <Text style={styles.rewardSuffix}>{settings.currencyName}</Text>
                    </View>
                    <Text style={styles.rangeText}>
                      Range: {CURRENCY_CONFIG.MIN_CHAT_REWARD} - {CURRENCY_CONFIG.MAX_CHAT_REWARD}
                    </Text>
                  </View>

                  <View style={styles.rewardContainer}>
                    <Text style={styles.inputLabel}>Event Reward</Text>
                    <Text style={styles.rewardDescription}>
                      Amount of {settings.currencyName} earned per event (follows, subscriptions, etc.)
                    </Text>
                    <View style={styles.rewardInputContainer}>
                      <TextInput
                        style={styles.rewardInput}
                        value={settings.eventReward.toString()}
                        onChangeText={(text) => {
                          const value = parseInt(text) || 0;
                          setSettings(prev => ({ ...prev, eventReward: value }));
                        }}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor={COLORS.TEXT_MUTED}
                      />
                      <Text style={styles.rewardSuffix}>{settings.currencyName}</Text>
                    </View>
                    <Text style={styles.rangeText}>
                      Range: {CURRENCY_CONFIG.MIN_EVENT_REWARD} - {CURRENCY_CONFIG.MAX_EVENT_REWARD}
                    </Text>
                  </View>

                  <View style={styles.currencyInfo}>
                    <Text style={styles.infoTitle}>Currency Activities:</Text>
                    <View style={styles.activityList}>
                      <View style={styles.activityItem}>
                        <Text style={styles.activityIcon}>💬</Text>
                        <Text style={styles.activityText}>Chat Messages</Text>
                        <Text style={styles.activityReward}>+{settings.chatMessageReward}</Text>
                      </View>
                      <View style={styles.activityItem}>
                        <Text style={styles.activityIcon}>⭐</Text>
                        <Text style={styles.activityText}>Subscriptions</Text>
                        <Text style={styles.activityReward}>+{settings.eventReward}</Text>
                      </View>
                      <View style={styles.activityItem}>
                        <Text style={styles.activityIcon}>👥</Text>
                        <Text style={styles.activityText}>Follows</Text>
                        <Text style={styles.activityReward}>+{settings.eventReward}</Text>
                      </View>
                      <View style={styles.activityItem}>
                        <Text style={styles.activityIcon}>💝</Text>
                        <Text style={styles.activityText}>Donations</Text>
                        <Text style={styles.activityReward}>+{settings.eventReward}</Text>
                      </View>
                    </View>
                  </View>
                </>
              )}
            </View>
          </View>
        )}

        <View style={styles.actionContainer}>
          <TouchableOpacity
            style={styles.cancelButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.cancelButtonText}>Cancel</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.saveButton, saving && styles.saveButtonDisabled]}
            onPress={handleSaveSettings}
            disabled={saving}
          >
            <Text style={styles.saveButtonText}>
              {saving ? 'Saving...' : 'Save Settings'}
            </Text>
          </TouchableOpacity>
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
  card: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  inputContainer: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  inputLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  input: {
    height: SIZES.INPUT_HEIGHT,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  textArea: {
    height: 100,
    paddingTop: SIZES.SPACING_MEDIUM,
  },
  switchContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  switchInfo: {
    flex: 1,
    marginRight: SIZES.SPACING_MEDIUM,
  },
  switchLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  switchDescription: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  thresholdContainer: {
    marginTop: SIZES.SPACING_MEDIUM,
    paddingTop: SIZES.SPACING_MEDIUM,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
  },
  thresholdDescription: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  thresholdDisplay: {
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  thresholdValue: {
    fontSize: SIZES.FONT_HERO,
    fontWeight: FONTS.WEIGHT_BOLD,
    marginBottom: SIZES.SPACING_TINY,
  },
  thresholdLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  slider: {
    width: '100%',
    height: 40,
    marginBottom: SIZES.SPACING_SMALL,
  },
  sliderLabels: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  sliderLabel: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  thresholdInfo: {
    marginTop: SIZES.SPACING_MEDIUM,
    paddingTop: SIZES.SPACING_MEDIUM,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
  },
  infoTitle: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  scoreRange: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  scoreIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginRight: SIZES.SPACING_SMALL,
  },
  scoreText: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  actionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: SIZES.SPACING_MEDIUM,
    marginTop: SIZES.SPACING_LARGE,
  },
  cancelButton: {
    flex: 1,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    borderWidth: 1,
    borderColor: COLORS.BORDER,
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  saveButton: {
    flex: 1,
    backgroundColor: COLORS.SECONDARY,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  saveButtonDisabled: {
    opacity: 0.7,
  },
  saveButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  // Currency styles
  rewardContainer: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  rewardDescription: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  rewardInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  rewardInput: {
    flex: 1,
    height: SIZES.INPUT_HEIGHT,
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderWidth: 1,
    borderColor: COLORS.INPUT_BORDER,
    borderRadius: SIZES.BUTTON_RADIUS,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    textAlign: 'center',
  },
  rewardSuffix: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginLeft: SIZES.SPACING_SMALL,
    minWidth: 60,
  },
  rangeText: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_MUTED,
    fontStyle: 'italic',
  },
  currencyInfo: {
    marginTop: SIZES.SPACING_MEDIUM,
    paddingTop: SIZES.SPACING_MEDIUM,
    borderTopWidth: 1,
    borderTopColor: COLORS.BORDER,
  },
  activityList: {
    marginTop: SIZES.SPACING_SMALL,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_SMALL,
  },
  activityIcon: {
    fontSize: SIZES.FONT_MEDIUM,
    marginRight: SIZES.SPACING_SMALL,
    width: 20,
  },
  activityText: {
    flex: 1,
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  activityReward: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.SUCCESS,
  },
});

export default CommunitySettingsScreen;