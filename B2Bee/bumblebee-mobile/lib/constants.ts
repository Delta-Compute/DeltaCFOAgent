export const API_BASE_URL = 'https://bumblebee-api-620026562181.southamerica-east1.run.app';

export const COLORS = {
  primary: '#F59E0B',
  primaryDark: '#D97706',
  primaryLight: '#FCD34D',
  background: '#0F172A',
  surface: '#1E293B',
  surfaceLight: '#334155',
  text: '#F8FAFC',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  success: '#10B981',
  error: '#EF4444',
  warning: '#F59E0B',
  info: '#3B82F6',
  border: '#334155',
  userBubble: '#3B82F6',
  assistantBubble: '#334155',
};

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export const BORDER_RADIUS = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

export const FONT_SIZE = {
  xs: 12,
  sm: 14,
  md: 16,
  lg: 18,
  xl: 20,
  xxl: 24,
  xxxl: 32,
};

export const ACTIVITY_CATEGORIES = {
  coding: { icon: 'code', color: '#8B5CF6' },
  communication: { icon: 'chatbubbles', color: '#10B981' },
  browsing: { icon: 'globe', color: '#3B82F6' },
  document: { icon: 'document-text', color: '#F59E0B' },
  meeting: { icon: 'videocam', color: '#EC4899' },
  other: { icon: 'apps', color: '#64748B' },
} as const;

export const STORAGE_KEYS = {
  API_KEY: 'bumblebee_api_key',
  ACCESS_TOKEN: 'bumblebee_access_token',
  REFRESH_TOKEN: 'bumblebee_refresh_token',
  USER_DATA: 'bumblebee_user',
  CHAT_SESSIONS: 'bumblebee_chat_sessions',
  CURRENT_SESSION: 'bumblebee_current_session',
};

export const POLLING_INTERVALS = {
  ACTIVITY: 30000,
  CHAT: 5000,
  GOALS: 60000,
};
