import { create } from 'zustand';
import * as SecureStore from 'expo-secure-store';
import { STORAGE_KEYS } from './constants';
import { User, ChatMessage, Settings, LoginResponse } from './types';
import { api } from './api';

interface AppState {
  apiKey: string | null;
  accessToken: string | null;
  refreshToken: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  currentChatSession: string | null;
  chatMessages: ChatMessage[];
  settings: Settings | null;
  error: string | null;

  setApiKey: (key: string | null) => Promise<void>;
  setTokens: (accessToken: string, refreshToken: string) => Promise<void>;
  loadTokens: () => Promise<void>;
  setUser: (user: User | null) => Promise<void>;
  setAuthenticated: (value: boolean) => void;
  setLoading: (value: boolean) => void;
  setCurrentChatSession: (sessionId: string | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  setChatMessages: (messages: ChatMessage[]) => void;
  clearChatMessages: () => void;
  setSettings: (settings: Settings | null) => void;
  setError: (error: string | null) => void;
  logout: () => Promise<void>;
  handleLoginSuccess: (response: LoginResponse) => Promise<void>;
}

export const useAppStore = create<AppState>((set, get) => ({
  apiKey: null,
  accessToken: null,
  refreshToken: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,
  currentChatSession: null,
  chatMessages: [],
  settings: null,
  error: null,

  setApiKey: async (key: string | null) => {
    if (key) {
      await SecureStore.setItemAsync(STORAGE_KEYS.API_KEY, key);
      api.setApiKey(key);
    } else {
      await SecureStore.deleteItemAsync(STORAGE_KEYS.API_KEY);
      api.setApiKey(null);
    }
    set({ apiKey: key });
  },

  setTokens: async (accessToken: string, refreshToken: string) => {
    await SecureStore.setItemAsync(STORAGE_KEYS.ACCESS_TOKEN, accessToken);
    await SecureStore.setItemAsync(STORAGE_KEYS.REFRESH_TOKEN, refreshToken);
    api.setAccessToken(accessToken);
    api.setRefreshToken(refreshToken);
    set({ accessToken, refreshToken });
  },

  loadTokens: async () => {
    try {
      // Try loading tokens first (new auth method)
      const accessToken = await SecureStore.getItemAsync(STORAGE_KEYS.ACCESS_TOKEN);
      const refreshToken = await SecureStore.getItemAsync(STORAGE_KEYS.REFRESH_TOKEN);
      const userJson = await SecureStore.getItemAsync(STORAGE_KEYS.USER_DATA);

      if (accessToken && refreshToken) {
        api.setAccessToken(accessToken);
        api.setRefreshToken(refreshToken);

        // Set up token refresh callback
        api.setOnTokenRefresh(async (newAccessToken) => {
          await SecureStore.setItemAsync(STORAGE_KEYS.ACCESS_TOKEN, newAccessToken);
          set({ accessToken: newAccessToken });
        });

        let user: User | null = null;
        if (userJson) {
          try {
            user = JSON.parse(userJson);
          } catch {}
        }

        set({ accessToken, refreshToken, user });
        return;
      }

      // Fall back to legacy API key auth
      const key = await SecureStore.getItemAsync(STORAGE_KEYS.API_KEY);
      if (key) {
        api.setApiKey(key);
        set({ apiKey: key });
      }
    } catch (error) {
      console.error('Failed to load auth:', error);
    } finally {
      set({ isLoading: false });
    }
  },

  setUser: async (user: User | null) => {
    if (user) {
      await SecureStore.setItemAsync(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    } else {
      await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
    }
    set({ user });
  },

  handleLoginSuccess: async (response: LoginResponse) => {
    const { setTokens, setUser, setAuthenticated, setError } = get();
    await setTokens(response.access_token, response.refresh_token);
    await setUser(response.user);
    setAuthenticated(true);
    setError(null);
  },

  setAuthenticated: (value: boolean) => set({ isAuthenticated: value }),

  setLoading: (value: boolean) => set({ isLoading: value }),

  setCurrentChatSession: (sessionId: string | null) =>
    set({ currentChatSession: sessionId }),

  addChatMessage: (message: ChatMessage) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),

  setChatMessages: (messages: ChatMessage[]) =>
    set({ chatMessages: messages }),

  clearChatMessages: () => set({ chatMessages: [] }),

  setSettings: (settings: Settings | null) => set({ settings }),

  setError: (error: string | null) => set({ error }),

  logout: async () => {
    await SecureStore.deleteItemAsync(STORAGE_KEYS.API_KEY);
    await SecureStore.deleteItemAsync(STORAGE_KEYS.ACCESS_TOKEN);
    await SecureStore.deleteItemAsync(STORAGE_KEYS.REFRESH_TOKEN);
    await SecureStore.deleteItemAsync(STORAGE_KEYS.USER_DATA);
    api.setApiKey(null);
    api.setAccessToken(null);
    api.setRefreshToken(null);
    api.setOnTokenRefresh(null);
    set({
      apiKey: null,
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      currentChatSession: null,
      chatMessages: [],
      settings: null,
      error: null,
    });
  },
}));
