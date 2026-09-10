import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as authApi from '../api/auth';
import * as promptsApi from '../api/prompts';
import * as usersApi from '../api/users';
import { ApiError } from '../api/client';
import type { UserPublic } from '../types/auth';

const mockAdminUser: UserPublic = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'admin@hitchings-gonzalez.com',
  role: 'admin',
  is_active: true,
  created_at: '2026-09-08T10:00:00Z',
  updated_at: '2026-09-08T10:00:00Z',
  last_login_at: '2026-09-08T10:00:00Z',
};

const mockRegularUser: UserPublic = {
  id: '22222222-2222-2222-2222-222222222222',
  email: 'abogado@hitchings-gonzalez.com',
  role: 'user',
  is_active: true,
  created_at: '2026-09-09T10:00:00Z',
  updated_at: '2026-09-09T10:00:00Z',
  last_login_at: '2026-09-09T12:00:00Z',
};

describe('Gestión de Usuarios Frontend (Bloque 7B)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue([]);
  });

  it('1. Usuario con role=admin ve el acceso a Configuración en la cabecera', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({
      users: [mockAdminUser, mockRegularUser],
      total: 2,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /análisis/i })).toBeInTheDocument();
    });
  });

  it('2. Usuario con role=user ve Configuración pero NO la pestaña de Usuarios', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /usuarios/i })).not.toBeInTheDocument();
    });
  });

  it('3. Administrador en Configuración accede a la pestaña Usuarios y ve la tabla', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({
      users: [mockAdminUser, mockRegularUser],
      total: 2,
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /usuarios/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /usuarios/i }));

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /gestión de cuentas y accesos/i })).toBeInTheDocument();
      expect(screen.getAllByText('admin@hitchings-gonzalez.com').length).toBeGreaterThanOrEqual(2);
      expect(screen.getByText('abogado@hitchings-gonzalez.com')).toBeInTheDocument();
      expect(screen.getByText('Administrador')).toBeInTheDocument();
      expect(screen.getByText('Usuario')).toBeInTheDocument();
      expect(screen.getAllByText('Activo').length).toBeGreaterThanOrEqual(2);
    });
  });


  it('4. Abre modal y crea un nuevo usuario exitosamente', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({
      users: [mockAdminUser],
      total: 1,
    });

    const createdUser: UserPublic = {
      id: '33333333-3333-3333-3333-333333333333',
      email: 'nuevo@hitchings.es',
      role: 'user',
      is_active: true,
      created_at: '2026-09-10T10:00:00Z',
      updated_at: '2026-09-10T10:00:00Z',
      last_login_at: null,
    };
    const createUserSpy = vi.spyOn(usersApi, 'createUser').mockResolvedValue(createdUser);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /usuarios/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('tab', { name: /usuarios/i }));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /nuevo usuario/i })).toBeInTheDocument();
    });
    fireEvent.click(screen.getByRole('button', { name: /nuevo usuario/i }));

    expect(screen.getByRole('heading', { name: /nuevo usuario/i })).toBeInTheDocument();

    const emailInput = screen.getByLabelText(/correo electrónico/i);
    const passInput = screen.getByLabelText(/^contraseña inicial/i);
    const confirmInput = screen.getByLabelText(/confirmar contraseña/i);
    const submitBtn = screen.getByRole('button', { name: /crear usuario/i });

    await userEvent.type(emailInput, 'nuevo@hitchings.es');
    await userEvent.type(passInput, 'PasswordSegura123!');
    await userEvent.type(confirmInput, 'PasswordSegura123!');

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createUserSpy).toHaveBeenCalledWith({
        email: 'nuevo@hitchings.es',
        role: 'user',
        password: 'PasswordSegura123!',
        confirm_password: 'PasswordSegura123!',
      });
      expect(screen.getByText('nuevo@hitchings.es')).toBeInTheDocument();
      expect(screen.getByText(/creado correctamente/i)).toBeInTheDocument();
    });
  });

  it('5. Valida contraseñas dispares en el formulario de creación', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser], total: 1 });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /nuevo usuario/i })));

    await userEvent.type(screen.getByLabelText(/correo electrónico/i), 'valida@hitchings.es');
    await userEvent.type(screen.getByLabelText(/^contraseña inicial/i), 'PasswordSegura123!');
    await userEvent.type(screen.getByLabelText(/confirmar contraseña/i), 'PasswordDiferente123!');

    fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }));

    await waitFor(() => {
      expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument();
    });
  });

  it('6. Muestra error ante conflicto de email duplicado (409)', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser], total: 1 });
    vi.spyOn(usersApi, 'createUser').mockRejectedValue(
      new ApiError('Ya existe un usuario registrado con ese correo electrónico.', 409)
    );

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /nuevo usuario/i })));

    await userEvent.type(screen.getByLabelText(/correo electrónico/i), 'admin@hitchings-gonzalez.com');
    await userEvent.type(screen.getByLabelText(/^contraseña inicial/i), 'PasswordSegura123!');
    await userEvent.type(screen.getByLabelText(/confirmar contraseña/i), 'PasswordSegura123!');

    fireEvent.click(screen.getByRole('button', { name: /crear usuario/i }));

    await waitFor(() => {
      expect(screen.getByText(/Ya existe un usuario registrado con ese correo electrónico/i)).toBeInTheDocument();
    });
  });

  it('7. Edita datos de un usuario mediante PATCH', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser, mockRegularUser], total: 2 });

    const updatedUser: UserPublic = {
      ...mockRegularUser,
      role: 'admin',
    };
    const updateSpy = vi.spyOn(usersApi, 'updateUser').mockResolvedValue(updatedUser);

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Editar a ${mockRegularUser.email}`)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(`Editar a ${mockRegularUser.email}`));

    expect(screen.getByRole('heading', { name: /editar usuario/i })).toBeInTheDocument();

    const roleSelect = screen.getByLabelText(/^rol/i);
    fireEvent.change(roleSelect, { target: { value: 'admin' } });

    fireEvent.click(screen.getByRole('button', { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(mockRegularUser.id, {
        email: undefined,
        role: 'admin',
        is_active: undefined,
      });
      expect(screen.getByText(/actualizado exitosamente/i)).toBeInTheDocument();
    });
  });

  it('8. Cambia la contraseña de otro usuario sin desloguear al admin', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser, mockRegularUser], total: 2 });
    const changePassSpy = vi.spyOn(usersApi, 'changeUserPassword').mockResolvedValue(mockRegularUser);

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Cambiar contraseña de ${mockRegularUser.email}`)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(`Cambiar contraseña de ${mockRegularUser.email}`));

    expect(screen.getByRole('heading', { name: /restablecer contraseña/i })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/^nueva contraseña/i), 'NuevaPassword1234!');
    await userEvent.type(screen.getByLabelText(/confirmar nueva contraseña/i), 'NuevaPassword1234!');

    fireEvent.click(screen.getByRole('button', { name: /actualizar contraseña/i }));

    await waitFor(() => {
      expect(changePassSpy).toHaveBeenCalledWith(mockRegularUser.id, {
        password: 'NuevaPassword1234!',
        confirm_password: 'NuevaPassword1234!',
      });
      expect(screen.getByText(/restablecida correctamente/i)).toBeInTheDocument();
    });
  });

  it('9. Si el admin cambia su propia contraseña, desloguea y redirige a login', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser], total: 1 });
    vi.spyOn(usersApi, 'changeUserPassword').mockResolvedValue(mockAdminUser);
    const logoutSpy = vi.spyOn(authApi, 'logout').mockResolvedValue({ message: 'Sesión cerrada.' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Cambiar contraseña de ${mockAdminUser.email}`)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(`Cambiar contraseña de ${mockAdminUser.email}`));

    await userEvent.type(screen.getByLabelText(/^nueva contraseña/i), 'NuevaPasswordAdmin1234!');
    await userEvent.type(screen.getByLabelText(/confirmar nueva contraseña/i), 'NuevaPasswordAdmin1234!');

    fireEvent.click(screen.getByRole('button', { name: /actualizar contraseña/i }));

    await waitFor(() => {
      expect(logoutSpy).toHaveBeenCalled();
      expect(screen.getByText(/acceso a la plataforma/i)).toBeInTheDocument();
    });
  });

  it('10. Desactivar usuario requiere confirmación en modal', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({ users: [mockAdminUser, mockRegularUser], total: 2 });
    const updateSpy = vi.spyOn(usersApi, 'updateUser').mockResolvedValue({ ...mockRegularUser, is_active: false });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('tab', { name: /usuarios/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Desactivar a ${mockRegularUser.email}`)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByLabelText(`Desactivar a ${mockRegularUser.email}`));

    // Se muestra modal de confirmación
    expect(screen.getByRole('heading', { name: /confirmar desactivación de usuario/i })).toBeInTheDocument();

    const confirmBtn = screen.getByRole('button', { name: /confirmar/i });
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(mockRegularUser.id, { is_active: false });
    });
  });
});
