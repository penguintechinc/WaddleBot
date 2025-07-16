import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Switch,
  Image,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { moduleService } from '../../services/moduleService';

const ModuleDetailScreen = ({ navigation, route }) => {
  const { communityId, moduleId } = route.params;
  const [module, setModule] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isInstalled, setIsInstalled] = useState(false);

  useEffect(() => {
    loadModuleDetails();
  }, [moduleId]);

  const loadModuleDetails = async () => {
    try {
      const moduleData = await moduleService.getModuleDetails(communityId, moduleId);
      setModule(moduleData);
      setIsInstalled(moduleData.isInstalled);
    } catch (error) {
      Alert.alert('Error', 'Failed to load module details');
      navigation.goBack();
    } finally {
      setLoading(false);
    }
  };

  const handleInstallModule = async () => {
    try {
      await moduleService.installModule(communityId, moduleId);
      Alert.alert('Success', 'Module installed successfully');
      setIsInstalled(true);
      loadModuleDetails();
    } catch (error) {
      Alert.alert('Error', 'Failed to install module');
    }
  };

  const handleUninstallModule = async () => {
    Alert.alert(
      'Uninstall Module',
      'Are you sure you want to uninstall this module?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Uninstall',
          style: 'destructive',
          onPress: async () => {
            try {
              await moduleService.uninstallModule(communityId, moduleId);
              Alert.alert('Success', 'Module uninstalled successfully');
              setIsInstalled(false);
              loadModuleDetails();
            } catch (error) {
              Alert.alert('Error', 'Failed to uninstall module');
            }
          }
        }
      ]
    );
  };

  const handleToggleModule = async () => {
    try {
      await moduleService.toggleModule(communityId, moduleId, !module.enabled);
      setModule({ ...module, enabled: !module.enabled });
    } catch (error) {
      Alert.alert('Error', 'Failed to toggle module');
    }
  };

  const getCategoryColor = (category) => {
    switch (category?.toLowerCase()) {
      case 'moderation':
        return COLORS.ERROR;
      case 'utility':
        return COLORS.INFO;
      case 'entertainment':
        return COLORS.SUCCESS;
      case 'analytics':
        return COLORS.WARNING;
      default:
        return COLORS.TEXT_SECONDARY;
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text style={styles.loadingText}>Loading module details...</Text>
      </View>
    );
  }

  if (!module) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Module not found</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <View style={styles.moduleIcon}>
          {module.icon ? (
            <Image source={{ uri: module.icon }} style={styles.iconImage} />
          ) : (
            <Text style={styles.iconText}>{module.name.charAt(0)}</Text>
          )}
        </View>
        <Text style={styles.moduleName}>{module.name}</Text>
        <Text style={styles.moduleAuthor}>by {module.author}</Text>
        <View style={styles.moduleMetaContainer}>
          <View style={[styles.categoryTag, { backgroundColor: getCategoryColor(module.category) }]}>
            <Text style={styles.categoryText}>{module.category}</Text>
          </View>
          <Text style={styles.moduleVersion}>v{module.version}</Text>
        </View>
      </View>

      <View style={styles.content}>
        <View style={styles.statsContainer}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>⭐ {module.rating}</Text>
            <Text style={styles.statLabel}>Rating</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{module.installCount}</Text>
            <Text style={styles.statLabel}>Installs</Text>
          </View>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{module.reviewCount}</Text>
            <Text style={styles.statLabel}>Reviews</Text>
          </View>
        </View>

        {isInstalled && (
          <View style={styles.controlsContainer}>
            <View style={styles.toggleContainer}>
              <Text style={styles.toggleLabel}>Module Enabled</Text>
              <Switch
                value={module.enabled}
                onValueChange={handleToggleModule}
                trackColor={{ false: COLORS.BORDER, true: COLORS.SECONDARY }}
                thumbColor={module.enabled ? COLORS.PRIMARY : COLORS.TEXT_MUTED}
              />
            </View>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Description</Text>
          <Text style={styles.sectionContent}>{module.description}</Text>
        </View>

        {module.longDescription && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Details</Text>
            <Text style={styles.sectionContent}>{module.longDescription}</Text>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Features</Text>
          {module.features?.map((feature, index) => (
            <View key={index} style={styles.featureItem}>
              <Text style={styles.featureBullet}>•</Text>
              <Text style={styles.featureText}>{feature}</Text>
            </View>
          ))}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Commands</Text>
          {module.commands?.map((command, index) => (
            <View key={index} style={styles.commandItem}>
              <Text style={styles.commandName}>{command.name}</Text>
              <Text style={styles.commandDescription}>{command.description}</Text>
            </View>
          ))}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Permissions Required</Text>
          {module.permissions?.map((permission, index) => (
            <View key={index} style={styles.permissionItem}>
              <Text style={styles.permissionName}>{permission.name}</Text>
              <Text style={styles.permissionReason}>{permission.reason}</Text>
            </View>
          ))}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Information</Text>
          <View style={styles.infoContainer}>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Version:</Text>
              <Text style={styles.infoValue}>{module.version}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Author:</Text>
              <Text style={styles.infoValue}>{module.author}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Category:</Text>
              <Text style={styles.infoValue}>{module.category}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Last Updated:</Text>
              <Text style={styles.infoValue}>
                {new Date(module.lastUpdated).toLocaleDateString()}
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Size:</Text>
              <Text style={styles.infoValue}>{module.size}</Text>
            </View>
          </View>
        </View>

        <View style={styles.actionContainer}>
          {isInstalled ? (
            <>
              <TouchableOpacity
                style={styles.configureButton}
                onPress={() => navigation.navigate('ModuleConfig', { 
                  communityId, 
                  moduleId: module.id 
                })}
              >
                <Text style={styles.configureButtonText}>Configure</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.uninstallButton}
                onPress={handleUninstallModule}
              >
                <Text style={styles.uninstallButtonText}>Uninstall</Text>
              </TouchableOpacity>
            </>
          ) : (
            <TouchableOpacity
              style={styles.installButton}
              onPress={handleInstallModule}
            >
              <Text style={styles.installButtonText}>Install Module</Text>
            </TouchableOpacity>
          )}
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
  moduleIcon: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.SECONDARY,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  iconImage: {
    width: 60,
    height: 60,
    borderRadius: 30,
  },
  iconText: {
    fontSize: SIZES.FONT_HERO,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  moduleName: {
    fontSize: SIZES.FONT_TITLE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  moduleAuthor: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  moduleMetaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SIZES.SPACING_MEDIUM,
  },
  categoryTag: {
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  categoryText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  moduleVersion: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  content: {
    padding: SIZES.SCREEN_MARGIN,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_LARGE,
    ...SHADOWS.LIGHT,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  statLabel: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  controlsContainer: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_LARGE,
    ...SHADOWS.LIGHT,
  },
  toggleContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  toggleLabel: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  section: {
    marginBottom: SIZES.SPACING_LARGE,
  },
  sectionTitle: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  sectionContent: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    lineHeight: 22,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: SIZES.SPACING_SMALL,
  },
  featureBullet: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.SECONDARY,
    marginRight: SIZES.SPACING_SMALL,
    marginTop: 2,
  },
  featureText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    flex: 1,
  },
  commandItem: {
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_SMALL,
  },
  commandName: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  commandDescription: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  permissionItem: {
    backgroundColor: COLORS.INPUT_BACKGROUND,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_SMALL,
  },
  permissionName: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  permissionReason: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  infoContainer: {
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
  },
  infoValue: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
    fontWeight: FONTS.WEIGHT_MEDIUM,
  },
  actionContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: SIZES.SPACING_MEDIUM,
    marginTop: SIZES.SPACING_LARGE,
  },
  installButton: {
    flex: 1,
    backgroundColor: COLORS.SUCCESS,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  installButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_LIGHT,
  },
  configureButton: {
    flex: 1,
    backgroundColor: COLORS.SECONDARY,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  configureButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
  },
  uninstallButton: {
    flex: 1,
    backgroundColor: COLORS.ERROR,
    paddingVertical: SIZES.SPACING_MEDIUM,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  uninstallButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_LIGHT,
  },
});

export default ModuleDetailScreen;