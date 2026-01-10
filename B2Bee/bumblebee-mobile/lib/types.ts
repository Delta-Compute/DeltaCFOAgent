export interface User {
  id: string;
  email: string;
  name: string;
  tenant_id: string;
  tenant_name?: string;
  created_at: string;
}

export interface AuthResponse {
  authenticated: boolean;
  tenant_id: string;
  user_id: string;
  features: string[];
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
  device_name?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  session_id?: string;
}

export interface ChatSession {
  session_id: string;
  title: string;
  message_count: number;
  created_at: string;
  last_message_at: string;
  last_message_preview?: string;
}

export interface ChatSessionDetail {
  session_id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  context_used?: string[];
  memory_updated?: boolean;
}

export interface DetectedContact {
  name: string;
  platform: string;
  confidence: number;
}

export interface Capture {
  id: string;
  timestamp: string;
  activity_category: string;
  insights: string;
  detected_contacts: DetectedContact[];
  sentiment?: string;
  application?: string;
  topics?: string[];
  thumbnail_url?: string;
}

export interface ActivitySummary {
  total_captures: number;
  today_captures: number;
  categories_breakdown: Record<string, number>;
  top_contacts: DetectedContact[];
  productivity_score?: number;
  daily_summary?: string;
}

export interface UnifiedContext {
  recent_activities: Capture[];
  active_contacts: DetectedContact[];
  current_focus?: string;
  coding_context?: CodingContext;
  communication_summary?: string;
}

export interface CodingContext {
  current_project?: string;
  recent_files: string[];
  languages_used: string[];
  time_spent_today: number;
  recent_commits?: string[];
}

export interface Goal {
  id: string;
  title: string;
  description?: string;
  target_value: number;
  current_value: number;
  unit: string;
  category: string;
  deadline?: string;
  created_at: string;
  updated_at: string;
  status: 'active' | 'completed' | 'paused';
}

export interface CreateGoal {
  title: string;
  description?: string;
  target_value: number;
  unit: string;
  category: string;
  deadline?: string;
}

export interface GoalRings {
  daily_progress: number;
  weekly_progress: number;
  monthly_progress: number;
  goals: Goal[];
}

export interface Note {
  id: string;
  content: string;
  source: 'voice' | 'text' | 'auto';
  tags?: string[];
  created_at: string;
  updated_at: string;
}

export interface Memory {
  id: string;
  content: string;
  category: string;
  relevance_score: number;
  source: string;
  created_at: string;
}

export interface Settings {
  voice_enabled: boolean;
  notifications_enabled: boolean;
  auto_capture: boolean;
  capture_interval: number;
  theme: 'dark' | 'light' | 'system';
  language: string;
}

export interface ApiError {
  error: string;
  message: string;
  status_code: number;
}
