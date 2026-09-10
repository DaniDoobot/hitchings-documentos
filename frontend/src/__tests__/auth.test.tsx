import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as authApi from '../api/auth';
import * as promptsApi from '../api/prompts';
import { getCsrfToken } from '../api/client';

const mockUser = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'admin@hitchings-gonzalez.com',
  role: 'admin',
  is_active: true,
  created_at: '2026-09-08T10:00:00Z',
  updated_at: '2026-09-08T10:00:00Z',
  last_login_at: '2026-09-08T10:00:00Z',
  csrf_token: 'valid-csrf-token-12345',
};

describe('Autenticación y Sesiones Frontend (Bloque 7A)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('1. Muestra pantalla de carga mientras verifica la sesión inicial (sin flash de contenido protegido)', async () => {
    let resolveGetMe: (val: any) => void;
    const pendingPromise = new Promise((resolve) => {
      resolveGetMe = resolve;
    });
    vi.spyOn(authApi, 'getMe').mockReturnValue(pendingPromise as any);

    render(<App />);

    // Verifica que se muestra la pantalla de carga y NO el contenido de la app
    expect(screen.getByText(/Verificando sesión segura.../i)).toBeInTheDocument();
    expect(screen.queryByText(/HITCHINGS Y GONZALEZ DOCUMENTOS/i)).not.toBeInTheDocument();

    // Resolver con no autenticado
    resolveGetMe!({ status: 401 });
  });

  it('2. Si no hay sesión válida, muestra la vista de login institucional con sus campos y branding', async () => {
    vi.spyOn(authApi, 'getMe').mockRejectedValue(new Error('Unauthorized'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Acceso a la plataforma/i)).toBeInTheDocument();
    });

    expect(screen.getByRole('heading', { name: /HITCHINGS Y GONZALEZ DOCUMENTOS/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Correo electrónico/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Contraseña/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Iniciar sesión/i })).toBeInTheDocument();

    // No debe haber enlaces de registro ni contenido protegido
    expect(screen.queryByText(/Registrarse/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /documento/i })).not.toBeInTheDocument();
  });

  it('3. El botón de login permanece deshabilitado si faltan credenciales', async () => {
    vi.spyOn(authApi, 'getMe').mockRejectedValue(new Error('Unauthorized'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Iniciar sesión/i })).toBeDisabled();
    });

    const emailInput = screen.getByLabelText(/Correo electrónico/i);
    await userEvent.type(emailInput, 'admin@hitchings.com');
    expect(screen.getByRole('button', { name: /Iniciar sesión/i })).toBeDisabled();
  });

  it('4. Muestra mensaje de error claro ante fallo de autenticación', async () => {
    vi.spyOn(authApi, 'getMe').mockRejectedValue(new Error('Unauthorized'));
    vi.spyOn(authApi, 'login').mockRejectedValue(new Error('Email o contraseña incorrectos.'));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Acceso a la plataforma/i)).toBeInTheDocument();
    });

    const emailInput = screen.getByLabelText(/Correo electrónico/i);
    const passwordInput = screen.getByLabelText(/Contraseña/i);
    const submitBtn = screen.getByRole('button', { name: /Iniciar sesión/i });

    await userEvent.type(emailInput, 'admin@hitchings.com');
    await userEvent.type(passwordInput, 'wrongpassword123');

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Email o contraseña incorrectos.');
    });
  });

  it('5. Flujo de login exitoso: autentica, almacena CSRF en memoria y muestra la aplicación protegida', async () => {
    vi.spyOn(authApi, 'getMe').mockRejectedValueOnce(new Error('Unauthorized'));
    vi.spyOn(authApi, 'login').mockResolvedValueOnce(mockUser);
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValueOnce([]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Acceso a la plataforma/i)).toBeInTheDocument();
    });

    const emailInput = screen.getByLabelText(/Correo electrónico/i);
    const passwordInput = screen.getByLabelText(/Contraseña/i);
    const submitBtn = screen.getByRole('button', { name: /Iniciar sesión/i });

    await userEvent.type(emailInput, 'admin@hitchings-gonzalez.com');
    await userEvent.type(passwordInput, 'validAdminPassword123#');

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText('admin@hitchings-gonzalez.com')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Cerrar sesión/i })).toBeInTheDocument();
    });

    // CSRF token almacenado estrictamente en memoria
    expect(getCsrfToken()).toBe('valid-csrf-token-12345');
  });

  it('6. Header muestra el email del usuario y permite cerrar sesión de inmediato', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(authApi, 'logout').mockResolvedValue({ message: 'Sesión cerrada exitosamente.' });
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue([]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('admin@hitchings-gonzalez.com')).toBeInTheDocument();
    });

    const logoutBtn = screen.getByRole('button', { name: /Cerrar sesión/i });
    fireEvent.click(logoutBtn);

    await waitFor(() => {
      expect(screen.getByText(/Acceso a la plataforma/i)).toBeInTheDocument();
    });

    expect(screen.queryByText('admin@hitchings-gonzalez.com')).not.toBeInTheDocument();
    expect(getCsrfToken()).toBeNull();
  });

  it('7. Si la carga de prompts retorna 401 (sesión expirada), desloguea automáticamente y muestra login', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue(mockUser);
    vi.spyOn(authApi, 'logout').mockResolvedValue({ message: 'Sesión cerrada.' });
    vi.spyOn(promptsApi, 'fetchPrompts').mockRejectedValue(
      new (await import('../api/client')).ApiError('No autenticado.', 401)
    );

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Acceso a la plataforma/i)).toBeInTheDocument();
    });

    expect(authApi.logout).toHaveBeenCalled();
  });

  it('8. Si la carga de prompts falla por error de red/servidor (no 401), muestra error y botón Reintentar', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue(mockUser);
    const fetchPromptsSpy = vi.spyOn(promptsApi, 'fetchPrompts')
      .mockRejectedValueOnce(new Error('Error al conectar con el servidor'))
      .mockResolvedValueOnce([
        {
          id: 'legal-analysis',
          name: 'Análisis Jurídico',
          description: 'Descripción',
          instructions: 'Instrucciones',
          is_active: true,
          is_system: true,
          created_at: '2026-09-08T10:00:00Z',
          updated_at: '2026-09-08T10:00:00Z',
        },
      ]);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText('Error al conectar con el servidor')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /reintentar/i })).toBeInTheDocument();
    });

    // Clic en reintentar debe invocar nuevamente fetchPrompts y cargar el prompt
    fireEvent.click(screen.getByRole('button', { name: /reintentar/i }));

    await waitFor(() => {
      expect(screen.queryByText('Error al conectar con el servidor')).not.toBeInTheDocument();
      expect(screen.getByDisplayValue('Análisis Jurídico')).toBeInTheDocument();
    });

    expect(fetchPromptsSpy).toHaveBeenCalledTimes(2);
  });
});
