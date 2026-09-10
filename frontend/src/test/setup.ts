import '@testing-library/jest-dom/vitest';
import * as authApi from '../api/auth';
import { vi, beforeEach } from 'vitest';

if (typeof window !== 'undefined' && window.HTMLElement) {
  window.HTMLElement.prototype.scrollIntoView = function () {};
}

beforeEach(() => {
  vi.spyOn(authApi, 'getMe').mockResolvedValue({
    id: '00000000-0000-0000-0000-000000000001',
    email: 'admin@hitchings-gonzalez.com',
    role: 'admin',
    is_active: true,
    created_at: '2026-09-08T10:00:00Z',
    last_login_at: '2026-09-08T10:00:00Z',
    csrf_token: 'mock-csrf-token',
  });
});

