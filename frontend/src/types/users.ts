import type { UserPublic } from './auth';

export interface UserListResponse {
  users: UserPublic[];
  total: number;
}

export interface UserCreatePayload {
  email: string;
  password: string;
  confirm_password?: string;
  role?: 'user' | 'admin';
}

export interface UserUpdatePayload {
  email?: string;
  role?: 'user' | 'admin';
  is_active?: boolean;
}

export interface UserChangePasswordPayload {
  password: string;
  confirm_password?: string;
}
