import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import type { UserPublic, LoginCredentials } from '../types/auth';
import * as authApi from '../api/auth';
import { setCsrfToken } from '../api/client';

interface AuthContextType {
  user: UserPublic | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  updateCurrentUser: (partial: Partial<UserPublic>) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;

    async function checkSession() {
      try {
        const response = await authApi.getMe();
        if (isMounted) {
          setUser({
            id: response.id,
            email: response.email,
            role: response.role,
            is_active: response.is_active,
            created_at: response.created_at,
            updated_at: response.updated_at,
            last_login_at: response.last_login_at,
          });
          setCsrfToken(response.csrf_token);
        }
      } catch {
        if (isMounted) {
          setUser(null);
          setCsrfToken(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    checkSession();

    return () => {
      isMounted = false;
    };
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    const response = await authApi.login(credentials);
    setUser({
      id: response.id,
      email: response.email,
      role: response.role,
      is_active: response.is_active,
      created_at: response.created_at,
      updated_at: response.updated_at,
      last_login_at: response.last_login_at,
    });
    setCsrfToken(response.csrf_token);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignorar errores en logout para garantizar limpieza de estado local
    } finally {
      setUser(null);
      setCsrfToken(null);
    }
  }, []);

  const updateCurrentUser = useCallback((partial: Partial<UserPublic>) => {
    setUser((prev) => (prev ? { ...prev, ...partial } : null));
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, updateCurrentUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth debe ser utilizado dentro de un AuthProvider');
  }
  return context;
}
