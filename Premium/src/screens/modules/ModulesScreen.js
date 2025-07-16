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
  Switch,
} from 'react-native';
import { COLORS, SIZES, FONTS, SHADOWS } from '../../constants/theme';
import { moduleService } from '../../services/moduleService';

const ModulesScreen = ({ navigation, route }) => {
  const { communityId } = route.params;
  const [modules, setModules] = useState([]);
  const [filteredModules, setFilteredModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [activeTab, setActiveTab] = useState('installed'); // 'installed', 'available'

  useEffect(() => {
    loadModules();
  }, [communityId, activeTab]);

  useEffect(() => {
    filterModules();
  }, [searchText, modules]);

  const loadModules = async () => {
    try {
      let modulesData;
      if (activeTab === 'installed') {
        modulesData = await moduleService.getInstalledModules(communityId);
      } else {
        modulesData = await moduleService.getAvailableModules(communityId);
      }
      setModules(modulesData);
      setFilteredModules(modulesData);
    } catch (error) {
      Alert.alert('Error', 'Failed to load modules');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadModules();
    setRefreshing(false);
  };

  const filterModules = () => {
    if (!searchText) {
      setFilteredModules(modules);
      return;
    }

    const filtered = modules.filter(module =>
      module.name.toLowerCase().includes(searchText.toLowerCase()) ||
      module.description.toLowerCase().includes(searchText.toLowerCase()) ||
      module.category.toLowerCase().includes(searchText.toLowerCase())
    );
    setFilteredModules(filtered);
  };

  const handleInstallModule = async (moduleId) => {
    try {
      await moduleService.installModule(communityId, moduleId);
      Alert.alert('Success', 'Module installed successfully');
      loadModules();
    } catch (error) {
      Alert.alert('Error', 'Failed to install module');
    }
  };

  const handleUninstallModule = async (moduleId) => {
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
              loadModules();
            } catch (error) {
              Alert.alert('Error', 'Failed to uninstall module');
            }
          }
        }
      ]
    );
  };

  const handleToggleModule = async (moduleId, currentEnabled) => {
    try {
      await moduleService.toggleModule(communityId, moduleId, !currentEnabled);
      const updatedModules = modules.map(module =>
        module.id === moduleId ? { ...module, enabled: !currentEnabled } : module
      );
      setModules(updatedModules);
    } catch (error) {
      Alert.alert('Error', 'Failed to toggle module');
    }
  };

  const getCategoryColor = (category) => {
    switch (category.toLowerCase()) {
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

  const ModuleItem = ({ module }) => (
    <TouchableOpacity
      style={styles.moduleItem}
      onPress={() => navigation.navigate('ModuleDetail', { 
        communityId, 
        moduleId: module.id 
      })}
    >
      <View style={styles.moduleHeader}>
        <View style={styles.moduleInfo}>
          <Text style={styles.moduleName}>{module.name}</Text>
          <Text style={styles.moduleAuthor}>by {module.author}</Text>
          <Text style={styles.moduleDescription} numberOfLines={2}>
            {module.description}
          </Text>
        </View>
        <View style={styles.moduleActions}>
          <View style={[styles.categoryTag, { backgroundColor: getCategoryColor(module.category) }]}>
            <Text style={styles.categoryText}>{module.category}</Text>
          </View>
          {activeTab === 'installed' && (
            <Switch
              value={module.enabled}
              onValueChange={() => handleToggleModule(module.id, module.enabled)}
              trackColor={{ false: COLORS.BORDER, true: COLORS.SECONDARY }}
              thumbColor={module.enabled ? COLORS.PRIMARY : COLORS.TEXT_MUTED}
            />
          )}
        </View>
      </View>

      <View style={styles.moduleFooter}>
        <View style={styles.moduleStats}>
          <Text style={styles.moduleVersion}>v{module.version}</Text>
          <Text style={styles.moduleRating}>⭐ {module.rating}</Text>
          <Text style={styles.moduleInstalls}>{module.installCount} installs</Text>
        </View>
        
        <View style={styles.moduleButtons}>
          {activeTab === 'installed' ? (
            <TouchableOpacity
              style={[styles.actionButton, styles.uninstallButton]}
              onPress={() => handleUninstallModule(module.id)}
            >
              <Text style={styles.uninstallButtonText}>Uninstall</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={[styles.actionButton, styles.installButton]}
              onPress={() => handleInstallModule(module.id)}
            >
              <Text style={styles.installButtonText}>Install</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Community Modules</Text>
        <TouchableOpacity
          style={styles.marketplaceButton}
          onPress={() => navigation.navigate('ModuleMarketplace', { communityId })}
        >
          <Text style={styles.marketplaceButtonText}>Marketplace</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.tabContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'installed' && styles.activeTab]}
          onPress={() => setActiveTab('installed')}
        >
          <Text style={[styles.tabText, activeTab === 'installed' && styles.activeTabText]}>
            Installed
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'available' && styles.activeTab]}
          onPress={() => setActiveTab('available')}
        >
          <Text style={[styles.tabText, activeTab === 'available' && styles.activeTabText]}>
            Available
          </Text>
        </TouchableOpacity>
      </View>

      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search modules..."
          placeholderTextColor={COLORS.TEXT_MUTED}
          value={searchText}
          onChangeText={setSearchText}
        />
      </View>

      <FlatList
        data={filteredModules}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <ModuleItem module={item} />}
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
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyStateText}>
              {activeTab === 'installed' ? 'No modules installed' : 'No modules available'}
            </Text>
            {activeTab === 'installed' && (
              <TouchableOpacity
                style={styles.browseButton}
                onPress={() => setActiveTab('available')}
              >
                <Text style={styles.browseButtonText}>Browse Available Modules</Text>
              </TouchableOpacity>
            )}
          </View>
        }
      />
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
  marketplaceButton: {
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  marketplaceButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: COLORS.INPUT_BACKGROUND,
    margin: SIZES.SCREEN_MARGIN,
    borderRadius: SIZES.BUTTON_RADIUS,
    padding: SIZES.SPACING_TINY,
  },
  tab: {
    flex: 1,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
    alignItems: 'center',
  },
  activeTab: {
    backgroundColor: COLORS.SECONDARY,
  },
  tabText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
  },
  activeTabText: {
    color: COLORS.TEXT_PRIMARY,
    fontWeight: FONTS.WEIGHT_BOLD,
  },
  searchContainer: {
    paddingHorizontal: SIZES.SCREEN_MARGIN,
    marginBottom: SIZES.SPACING_MEDIUM,
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
  moduleItem: {
    backgroundColor: COLORS.CARD_BACKGROUND,
    borderRadius: SIZES.CARD_RADIUS,
    padding: SIZES.SPACING_MEDIUM,
    marginBottom: SIZES.SPACING_MEDIUM,
    ...SHADOWS.LIGHT,
  },
  moduleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  moduleInfo: {
    flex: 1,
    marginRight: SIZES.SPACING_MEDIUM,
  },
  moduleName: {
    fontSize: SIZES.FONT_LARGE,
    fontWeight: FONTS.WEIGHT_BOLD,
    color: COLORS.TEXT_PRIMARY,
    marginBottom: SIZES.SPACING_TINY,
  },
  moduleAuthor: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_SMALL,
  },
  moduleDescription: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    lineHeight: 20,
  },
  moduleActions: {
    alignItems: 'flex-end',
  },
  categoryTag: {
    paddingHorizontal: SIZES.SPACING_SMALL,
    paddingVertical: SIZES.SPACING_TINY,
    borderRadius: SIZES.BUTTON_RADIUS,
    marginBottom: SIZES.SPACING_SMALL,
  },
  categoryText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  moduleFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  moduleStats: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SIZES.SPACING_MEDIUM,
  },
  moduleVersion: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  moduleRating: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  moduleInstalls: {
    fontSize: SIZES.FONT_SMALL,
    color: COLORS.TEXT_SECONDARY,
  },
  moduleButtons: {
    flexDirection: 'row',
    gap: SIZES.SPACING_SMALL,
  },
  actionButton: {
    paddingHorizontal: SIZES.SPACING_MEDIUM,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  installButton: {
    backgroundColor: COLORS.SUCCESS,
  },
  installButtonText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  uninstallButton: {
    backgroundColor: COLORS.ERROR,
  },
  uninstallButtonText: {
    fontSize: SIZES.FONT_SMALL,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_LIGHT,
  },
  emptyState: {
    alignItems: 'center',
    padding: SIZES.SPACING_XXLARGE,
  },
  emptyStateText: {
    fontSize: SIZES.FONT_MEDIUM,
    color: COLORS.TEXT_SECONDARY,
    marginBottom: SIZES.SPACING_MEDIUM,
  },
  browseButton: {
    backgroundColor: COLORS.SECONDARY,
    paddingHorizontal: SIZES.SPACING_LARGE,
    paddingVertical: SIZES.SPACING_SMALL,
    borderRadius: SIZES.BUTTON_RADIUS,
  },
  browseButtonText: {
    fontSize: SIZES.FONT_MEDIUM,
    fontWeight: FONTS.WEIGHT_MEDIUM,
    color: COLORS.TEXT_PRIMARY,
  },
});

export default ModulesScreen;