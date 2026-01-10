import { API_BASE_URL } from './constants';
import {
  AuthResponse,
  LoginResponse,
  RefreshResponse,
  ChatResponse,
  ChatSession,
  ChatSessionDetail,
  Capture,
  ActivitySummary,
  UnifiedContext,
  Goal,
  CreateGoal,
  GoalRings,
  Note,
  Memory,
  Settings,
  ApiError,
} from './types';

class BumbleBeeAPI {
  private apiKey: string | null = null;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private onTokenRefresh: ((accessToken: string) => void) | null = null;
  readonly baseUrl = API_BASE_URL;

  setApiKey(key: string | null) {
    this.apiKey = key;
  }

  getApiKey(): string | null {
    return this.apiKey;
  }

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  setRefreshToken(token: string | null) {
    this.refreshToken = token;
  }

  setOnTokenRefresh(callback: ((accessToken: string) => void) | null) {
    this.onTokenRefresh = callback;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    skipAuth: boolean = false
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    };

    // Use Bearer token auth (preferred) or API key (legacy)
    if (!skipAuth) {
      if (this.accessToken) {
        headers['Authorization'] = `Bearer ${this.accessToken}`;
      } else if (this.apiKey) {
        headers['X-API-Key'] = this.apiKey;
      }
    }

    let response = await fetch(url, {
      ...options,
      headers,
    });

    // If 401 and we have a refresh token, try to refresh
    if (response.status === 401 && this.refreshToken && this.accessToken) {
      const refreshed = await this.tryRefreshToken();
      if (refreshed) {
        // Retry the request with new token
        headers['Authorization'] = `Bearer ${this.accessToken}`;
        response = await fetch(url, {
          ...options,
          headers,
        });
      }
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      const error: ApiError = {
        error: errorData.error || errorData.detail || 'Request failed',
        message: errorData.message || errorData.detail || `HTTP ${response.status}`,
        status_code: response.status,
      };
      throw error;
    }

    return response.json();
  }

  private async tryRefreshToken(): Promise<boolean> {
    if (!this.refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });

      if (response.ok) {
        const data: RefreshResponse = await response.json();
        this.accessToken = data.access_token;
        if (this.onTokenRefresh) {
          this.onTokenRefresh(data.access_token);
        }
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
    return false;
  }

  async login(email: string, password: string, deviceName?: string): Promise<LoginResponse> {
    return this.request<LoginResponse>(
      '/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({
          email,
          password,
          device_name: deviceName || 'BumbleBee Mobile',
        }),
      },
      true // Skip auth headers for login
    );
  }

  async auth(): Promise<AuthResponse> {
    return this.request<AuthResponse>('/auth/me');
  }

  async sendMessage(
    content: string,
    sessionId?: string
  ): Promise<ChatResponse> {
    const body: Record<string, string> = { message: content };
    if (sessionId) {
      body.session_id = sessionId;
    }

    return this.request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify(body),
    });
  }

  async getSessions(): Promise<ChatSession[]> {
    const response = await this.request<{ sessions: ChatSession[] }>(
      '/chat/sessions'
    );
    return response.sessions;
  }

  async getSession(sessionId: string): Promise<ChatSessionDetail> {
    return this.request<ChatSessionDetail>(`/chat/sessions/${sessionId}`);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.request(`/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async getCaptures(limit: number = 20): Promise<Capture[]> {
    const response = await this.request<{ captures: Capture[] }>(
      `/captures?limit=${limit}`
    );
    return response.captures;
  }

  async getActivitySummary(): Promise<ActivitySummary> {
    return this.request<ActivitySummary>('/activity/summary');
  }

  async getContext(): Promise<UnifiedContext> {
    return this.request<UnifiedContext>('/context');
  }

  async getGoals(): Promise<Goal[]> {
    const response = await this.request<{ goals: Goal[] }>('/goals');
    return response.goals;
  }

  async createGoal(goal: CreateGoal): Promise<Goal> {
    return this.request<Goal>('/goals', {
      method: 'POST',
      body: JSON.stringify(goal),
    });
  }

  async updateGoal(id: string, updates: Partial<Goal>): Promise<Goal> {
    return this.request<Goal>(`/goals/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  async updateGoalProgress(id: string, value: number): Promise<Goal> {
    return this.request<Goal>(`/goals/${id}/progress`, {
      method: 'POST',
      body: JSON.stringify({ value }),
    });
  }

  async deleteGoal(id: string): Promise<void> {
    await this.request(`/goals/${id}`, {
      method: 'DELETE',
    });
  }

  async getGoalRings(): Promise<GoalRings> {
    return this.request<GoalRings>('/goals/rings');
  }

  async getNotes(): Promise<Note[]> {
    const response = await this.request<{ notes: Note[] }>('/notes');
    return response.notes;
  }

  async createNote(
    content: string,
    source: 'voice' | 'text' = 'text'
  ): Promise<Note> {
    return this.request<Note>('/notes', {
      method: 'POST',
      body: JSON.stringify({ content, source }),
    });
  }

  async deleteNote(id: string): Promise<void> {
    await this.request(`/notes/${id}`, {
      method: 'DELETE',
    });
  }

  async searchMemory(query: string): Promise<Memory[]> {
    const response = await this.request<{ memories: Memory[] }>(
      `/memory/search?q=${encodeURIComponent(query)}`
    );
    return response.memories;
  }

  async getSettings(): Promise<Settings> {
    return this.request<Settings>('/settings');
  }

  async updateSettings(settings: Partial<Settings>): Promise<Settings> {
    return this.request<Settings>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }
}

export const api = new BumbleBeeAPI();
export default api;
