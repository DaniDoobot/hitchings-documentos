import { apiFetch } from './client';
import type { UserPublic } from '../types/auth';
import type {
  UserListResponse,
  UserCreatePayload,
  UserUpdatePayload,
  UserChangePasswordPayload,
} from '../types/users';

export type {
  UserListResponse,
  UserCreatePayload,
  UserUpdatePayload,
  UserChangePasswordPayload,
};

/**
 * Obtiene la lista completa de usuarios registrados en el sistema.
 * Requiere rol de administrador.
 */
export async function listUsers(): Promise<UserListResponse> {
  return apiFetch<UserListResponse>('/api/v1/admin/users');
}

/**
 * Da de alta un nuevo usuario en la plataforma.
 * Requiere rol de administrador y token CSRF.
 */
export async function createUser(payload: UserCreatePayload): Promise<UserPublic> {
  return apiFetch<UserPublic>('/api/v1/admin/users', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Modifica parcialmente los datos de un usuario existente (email, rol, is_active).
 * Requiere rol de administrador y token CSRF.
 */
export async function updateUser(
  userId: string,
  payload: UserUpdatePayload
): Promise<UserPublic> {
  return apiFetch<UserPublic>(`/api/v1/admin/users/${userId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Restablece la contraseña de un usuario y revoca todas sus sesiones activas.
 * Requiere rol de administrador y token CSRF.
 */
export async function changeUserPassword(
  userId: string,
  payload: UserChangePasswordPayload
): Promise<UserPublic> {
  return apiFetch<UserPublic>(`/api/v1/admin/users/${userId}/password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
