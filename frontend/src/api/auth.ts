import { apiFetch } from './client';
import type { AuthResponse, LoginCredentials } from '../types/auth';

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });
}

export async function getMe(): Promise<AuthResponse> {
  return apiFetch<AuthResponse>('/api/v1/auth/me', {
    method: 'GET',
  });
}

export async function logout(): Promise<{ message: string }> {
  return apiFetch<{ message: string }>('/api/v1/auth/logout', {
    method: 'POST',
  });
}
