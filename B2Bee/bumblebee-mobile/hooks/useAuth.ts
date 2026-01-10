import { useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../lib/store';
import { api } from '../lib/api';
import { AuthResponse, LoginResponse } from '../lib/types';

export function useAuth() {
  const queryClient = useQueryClient();
  const {
    apiKey,
    accessToken,
    user,
    isAuthenticated,
    isLoading,
    setApiKey,
    loadTokens,
    setAuthenticated,
    setError,
    logout,
    handleLoginSuccess,
  } = useAppStore();

  useEffect(() => {
    loadTokens();
  }, [loadTokens]);

  // Check if we have valid credentials (either token or API key)
  const hasCredentials = !!accessToken || !!apiKey;

  const authQuery = useQuery({
    queryKey: ['auth'],
    queryFn: () => api.auth(),
    enabled: hasCredentials,
    retry: 1,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (authQuery.isSuccess) {
      setAuthenticated(true);
      setError(null);
    } else if (authQuery.isError) {
      setAuthenticated(false);
      setError('Authentication failed');
    }
  }, [authQuery.isSuccess, authQuery.isError, setAuthenticated, setError]);

  // Email/password login mutation
  const loginMutation = useMutation({
    mutationFn: async ({ email, password }: { email: string; password: string }) => {
      return api.login(email, password);
    },
    onSuccess: async (response: LoginResponse) => {
      await handleLoginSuccess(response);
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
    onError: (error: Error) => {
      setAuthenticated(false);
      setError(error.message || 'Login failed');
    },
  });

  // Legacy API key login mutation
  const apiKeyLoginMutation = useMutation({
    mutationFn: async (key: string) => {
      api.setApiKey(key);
      const response = await api.auth();
      return { key, response };
    },
    onSuccess: async ({ key }) => {
      await setApiKey(key);
      setAuthenticated(true);
      setError(null);
      queryClient.invalidateQueries({ queryKey: ['auth'] });
    },
    onError: (error: Error) => {
      api.setApiKey(null);
      setAuthenticated(false);
      setError(error.message || 'Login failed');
    },
  });

  const handleLogout = useCallback(async () => {
    await logout();
    queryClient.clear();
  }, [logout, queryClient]);

  const loginWithEmail = useCallback(
    async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
      try {
        await loginMutation.mutateAsync({ email, password });
        return { success: true };
      } catch (error: any) {
        const message = error?.message || error?.error || 'Login failed';
        return { success: false, error: message };
      }
    },
    [loginMutation]
  );

  return {
    apiKey,
    accessToken,
    user,
    isAuthenticated,
    isLoading: isLoading || authQuery.isLoading,
    authData: authQuery.data as AuthResponse | undefined,
    error: authQuery.error?.message,
    // Email/password login
    loginWithEmail,
    isLoggingIn: loginMutation.isPending,
    // Legacy API key login
    loginWithApiKey: apiKeyLoginMutation.mutate,
    isLoggingInWithApiKey: apiKeyLoginMutation.isPending,
    logout: handleLogout,
    refetchAuth: authQuery.refetch,
  };
}
