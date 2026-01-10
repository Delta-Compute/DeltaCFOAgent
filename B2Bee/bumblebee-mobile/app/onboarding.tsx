import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '../hooks/useAuth';
import { COLORS, SPACING, BORDER_RADIUS, FONT_SIZE } from '../lib/constants';

export default function OnboardingScreen() {
  const router = useRouter();
  const { loginWithEmail, isLoggingIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = useCallback(async () => {
    if (!email.trim()) {
      setError('Please enter your email');
      return;
    }

    if (!password) {
      setError('Please enter your password');
      return;
    }

    setError(null);

    const result = await loginWithEmail(email.trim(), password);
    if (!result.success) {
      setError(result.error || 'Login failed. Please check your credentials.');
    }
  }, [email, password, loginWithEmail]);

  const handleSignUp = useCallback(() => {
    Linking.openURL('https://b2bee.tech/signup');
  }, []);

  const handleForgotPassword = useCallback(() => {
    Linking.openURL('https://b2bee.tech/forgot-password');
  }, []);

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={styles.keyboardView}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <View style={styles.content}>
          <View style={styles.logoContainer}>
            <View style={styles.logo}>
              <Text style={styles.logoText}>B</Text>
            </View>
            <Text style={styles.title}>BumbleBee</Text>
            <Text style={styles.subtitle}>
              Your AI assistant that syncs with your desktop
            </Text>
          </View>

          <View style={styles.formContainer}>
            <Text style={styles.label}>Email</Text>
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={(text) => {
                  setEmail(text);
                  setError(null);
                }}
                placeholder="Enter your email"
                placeholderTextColor={COLORS.textMuted}
                keyboardType="email-address"
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="email"
              />
            </View>

            <Text style={[styles.label, { marginTop: SPACING.lg }]}>Password</Text>
            <View style={styles.inputContainer}>
              <TextInput
                style={styles.input}
                value={password}
                onChangeText={(text) => {
                  setPassword(text);
                  setError(null);
                }}
                placeholder="Enter your password"
                placeholderTextColor={COLORS.textMuted}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="password"
              />
              <TouchableOpacity
                style={styles.eyeButton}
                onPress={() => setShowPassword(!showPassword)}
              >
                <Ionicons
                  name={showPassword ? 'eye-off' : 'eye'}
                  size={20}
                  color={COLORS.textMuted}
                />
              </TouchableOpacity>
            </View>

            {error && (
              <View style={styles.errorContainer}>
                <Ionicons name="alert-circle" size={16} color={COLORS.error} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <TouchableOpacity
              style={[
                styles.connectButton,
                (!email.trim() || !password || isLoggingIn) && styles.connectButtonDisabled,
              ]}
              onPress={handleLogin}
              disabled={!email.trim() || !password || isLoggingIn}
            >
              {isLoggingIn ? (
                <ActivityIndicator color={COLORS.background} />
              ) : (
                <>
                  <Text style={styles.connectButtonText}>Sign In</Text>
                  <Ionicons name="arrow-forward" size={20} color={COLORS.background} />
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity style={styles.helpButton} onPress={handleForgotPassword}>
              <Text style={styles.helpText}>Forgot password?</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.features}>
            <View style={styles.featureItem}>
              <Ionicons name="chatbubbles" size={24} color={COLORS.primary} />
              <Text style={styles.featureText}>Chat with BumbleBee AI</Text>
            </View>
            <View style={styles.featureItem}>
              <Ionicons name="eye" size={24} color={COLORS.success} />
              <Text style={styles.featureText}>See desktop activity insights</Text>
            </View>
            <View style={styles.featureItem}>
              <Ionicons name="flag" size={24} color={COLORS.info} />
              <Text style={styles.featureText}>Track goals and progress</Text>
            </View>
          </View>

          <View style={styles.signupContainer}>
            <Text style={styles.signupText}>Don't have an account?</Text>
            <TouchableOpacity onPress={handleSignUp}>
              <Text style={styles.signupLink}>Sign up at b2bee.tech</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  keyboardView: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: SPACING.xl,
    justifyContent: 'center',
  },
  logoContainer: {
    alignItems: 'center',
    marginBottom: SPACING.xxl,
  },
  logo: {
    width: 100,
    height: 100,
    borderRadius: 50,
    backgroundColor: COLORS.primary,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: SPACING.lg,
  },
  logoText: {
    fontSize: 48,
    fontWeight: '700',
    color: COLORS.background,
  },
  title: {
    fontSize: FONT_SIZE.xxxl,
    fontWeight: '700',
    color: COLORS.text,
    marginBottom: SPACING.sm,
  },
  subtitle: {
    fontSize: FONT_SIZE.md,
    color: COLORS.textSecondary,
    textAlign: 'center',
  },
  formContainer: {
    marginBottom: SPACING.xxl,
  },
  label: {
    fontSize: FONT_SIZE.sm,
    fontWeight: '600',
    color: COLORS.textSecondary,
    marginBottom: SPACING.sm,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: BORDER_RADIUS.md,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  input: {
    flex: 1,
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.lg,
    fontSize: FONT_SIZE.md,
    color: COLORS.text,
  },
  eyeButton: {
    padding: SPACING.lg,
  },
  errorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: SPACING.sm,
    gap: SPACING.xs,
  },
  errorText: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.error,
  },
  connectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: COLORS.primary,
    borderRadius: BORDER_RADIUS.md,
    paddingVertical: SPACING.lg,
    marginTop: SPACING.lg,
    gap: SPACING.sm,
  },
  connectButtonDisabled: {
    opacity: 0.5,
  },
  connectButtonText: {
    fontSize: FONT_SIZE.md,
    fontWeight: '600',
    color: COLORS.background,
  },
  helpButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: SPACING.lg,
    gap: SPACING.xs,
  },
  helpText: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.primary,
  },
  features: {
    gap: SPACING.lg,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACING.md,
  },
  featureText: {
    fontSize: FONT_SIZE.md,
    color: COLORS.textSecondary,
  },
  signupContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: SPACING.xl,
    gap: SPACING.xs,
  },
  signupText: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.textSecondary,
  },
  signupLink: {
    fontSize: FONT_SIZE.sm,
    color: COLORS.primary,
    fontWeight: '600',
  },
});
