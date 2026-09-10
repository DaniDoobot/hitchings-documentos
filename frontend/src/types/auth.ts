export interface UserPublic {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
}

export interface AuthResponse {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
  csrf_token: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
}
