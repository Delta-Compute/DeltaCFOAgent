import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Switch,
  Alert,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../../hooks/useAuth';
import { useAppStore } from '../../lib/store';
import { API_BASE_URL, COLORS, SPACING, BORDER_RADIUS, FONT_SIZE } from '../../lib/constants';
import Constants from 'expo-constants';

export default function ProfileScreen() {
  const { authData, user, logout } = useAuth();
  const { apiKey, accessToken, settings, setSettings } = useAppStore();
  const [showApiKey, setShowApiKey] = useState(false);

  const appVersion = Constants.expoConfig?.version || '1.0.0';

  const defaultSettings = {
    voice_enabled: true,
    notifications_enabled: true,
    auto_capture: true,
    capture_interval: 30,
    theme: 'dark' as const,
    language: 'en',
  };

  // Get display name from user or fallback
  const displayName = user?.name || 'BumbleBee User';
  const displayEmail = user?.email || '';
  const tenantName = user?.tenant_name || authData?.tenant_id || '';

  const handleToggleVoice = useCallback(
    (value: boolean) => {
      setSettings({
        ...defaultSettings,
        ...settings,
        voice_enabled: value,
      });
    },
    [settings, setSettings]
  );

  const handleToggleNotifications = useCallback(
    (value: boolean) => {
      setSettings({
        ...defaultSettings,
        ...settings,
        notifications_enabled: value,
      });
    },
    [settings, setSettings]
  );

  const handleLogout = useCallback(() => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: logout,
        },
      ],
      { cancelable: true }
    );
  }, [logout]);

  const handleOpenDocs = useCallback(() => {
    Linking.openURL('https://github.com/Delta-Compute/bumblebee');
  }, []);

  // Get first letter for avatar
  const avatarLetter = displayName ? displayName.charAt(0).toUpperCase() : 'B';

  return (
    <SafeAreaView style={styles.container} edges={['bottom']}>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.header}>
          <View style={styles.avatarContainer}>
            <Text style={styles.avatarText}>{avatarLetter}</Text>
          </View>
          <Text style={styles.userName}>{displayName}</Text>
          {displayEmail && (
            <Text style={styles.userEmail}>{displayEmail}</Text>
          )}
          {tenantName && (
            <Text style={styles.tenantId}>{tenantName}</Text>
          )}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Account</Text>

          {displayEmail && (
            <View style={styles.settingItem}>
              <View style={styles.settingInfo}>
                <Ionicons name="mail" size={20} color={COLORS.primary} />
                <Text style={styles.settingLabel}>Email</Text>
              </View>
              <Text style={styles.settingValue}>{displayEmail}</Text>
            </View>
          )}

          <View style={styles.settingItem}>
            <View style={styles.settingInfo}>
              <Ionicons name="shield-checkmark" size={20} color={COLORS.success} />
              <Text style={styles.settingLabel}>Authentication</Text>
            </View>
            <Text style={styles.settingValue}>
              {accessToken ? 'Signed in' : apiKey ? 'API Key' : 'Not signed in'}
            </Text>
          </View>

          <View style={styles.settingItem}>
            <View style={styles.settingInfo}>
              <Ionicons name="server" size={20} color={COLORS.info} />
              <Text style={styles.settingLabel}>Backend</Text>
            </View>
            <Text style={styles.settingValue} numberOfLines={1}>
              Connected
            </Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Preferences</Text>

          <View style={styles.settingItem}>
            <View style={styles.settingInfo}>
              <Ionicons name="mic" size={20} color={COLORS.success} />
              <View>
                <Text style={styles.settingLabel}>Voice Assistant</Text>
                <Text style={styles.settingDescription}>
                  Enable voice input and TTS
                </Text>
              </View>
            </View>
            <Switch
              value={settings?.voice_enabled !== false}
              onValueChange={handleToggleVoice}
              trackColor={{ false: COLORS.surfaceLight, true: COLORS.primary + '60' }}
              thumbColor={settings?.voice_enabled !== false ? COLORS.primary : COLORS.textMuted}
            />
          </View>

          <View style={styles.settingItem}>
            <View style={styles.settingInfo}>
              <Ionicons name="notifications" size={20} color={COLORS.warning} />
              <View>
                <Text style={styles.settingLabel}>Notifications</Text>
                <Text style={styles.settingDescription}>
                  Receive activity alerts
                </Text>
              </View>
            </View>
            <Switch
              value={settings?.notifications_enabled !== false}
              onValueChange={handleToggleNotifications}
              trackColor={{ false: COLORS.surfaceLight, true: COLORS.primary + '60' }}
              thumbColor={settings?.notifications_enabled !== false ? COLORS.primary : COLORS.textMuted}
            />
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>About</Text>

          <TouchableOpacity style={styles.settingItem} onPress={handleOpenDocs}>
            <View style={styles.settingInfo}>
              <Ionicons name="document-text" size={20} color={COLORS.textSecondary} />
              <Text style={styles.settingLabel}>Documentation</Text>
            </View>
            <Ionicons name="open-outline" size={18} color={COLORS.textMuted} />
          </TouchableOpacity>

          <View style={styles.settingItem}>
            <View style={styles.settingInfo}>
              <Ionicons name="information-circle" size={20} color={COLORS.textSecondary} />
              <Text style={styles.settingLabel}>App Version</Text>
            </View>
            <Text style={styles.settingValue}>{appVersion}</Text>
          </View>

          {authData?.features && (
            <View style={styles.settingItem}>
              <View style={styles.settingInfo}>
                <Ionicons name="list" size={20} color={COLORS.textSecondary} />
                <Text style={styles.settingLabel}>Features</Text>
              </View>
              <Text style={styles.settingValue}>
                {authData.features.length} enabled
              </Text>
            </View>
          )}
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
          <Ionicons name="log-out" size={20} color={COLORS.error} />
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>

        <Text style={styles.footer}>
          BumbleBee Mobile v{appVersion}
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: SPACING.lg,
    paddingBottom: SPACING.xxl,
  },
  header: {
    alignItems: 'center',
    paddingVertical: SPACING.xl,
  },
  avatarContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.md,
  },
  avatarText: {
    fontSize: 36,
    fontWeight: '700',
    color: COLORS.background,
  },
  userName: {
    fontSize: FONT_SIZE.xl,
    fontWeight: '600',
    color: COLORS.text,
  },
  userEmail: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.textSecondary,
    marginTop: SPACING.xs,
  },
  tenantId: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.textMuted,
    marginTop: SPACING.xs,
  },
  section: {
    marginBottom: SPACING.xl,
  },
  sectionTitle: {
    fontSize: FONT_SIZE.sm,
    fontWeight: '600',
    color: COLORS.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 1,
    marginBottom: SPACING.md,
  },
  settingItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: COLORS.surface,
    padding: SPACING.lg,
    borderRadius: BORDER_RADIUS.md,
    marginBottom: SPACING.sm,
  },
  settingInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    gap: SPACING.md,
  },
  settingLabel: {
    fontSize: FONT_SIZE.md,
    color: COLORS.text,
  },
  settingDescription: {
    fontSize: FONT_SIZE.xs,
    color: COLORS.textMuted,
    marginTop: 2,
  },
  settingValue: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.textSecondary,
    maxWidth: '50%',
  },
  apiKeyContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.sm,
  },
  apiKeyText: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.textSecondary,
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
  },
  apiKeyInput: {
    backgroundColor: COLORS.surfaceLight,
    borderRadius: BORDER_RADIUS.sm,
    paddingHorizontal: SPACING.sm,
    paddingVertical: SPACING.xs,
    fontSize: FONT_SIZE.sm,
    color: COLORS.text,
    minWidth: 150,
  },
  iconButton: {
    padding: SPACING.xs,
  },
  logoutButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.error + '20',
    padding: SPACING.lg,
    borderRadius: BORDER_RADIUS.md,
    gap: SPACING.sm,
    marginTop: SPACING.lg,
  },
  logoutText: {
    fontSize: FONT_SIZE.md,
    fontWeight: '600',
    color: COLORS.error,
  },
  footer: {
    fontSize: FONT_SIZE.xs,
    color: COLORS.textMuted,
    textAlign: 'center',
    marginTop: SPACING.xl,
  },
});
