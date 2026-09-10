import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  UserPlus,
  Shield,
  UserCheck,
  UserX,
  KeyRound,
  Edit2,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  X,
  Loader2,
  AlertTriangle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import * as usersApi from '../api/users';
import { ApiError } from '../api/client';
import type { UserPublic } from '../types/auth';

export const UsersManagement: React.FC = () => {
  const { user: currentUser, logout, updateCurrentUser } = useAuth();

  const [users, setUsers] = useState<UserPublic[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [editingUser, setEditingUser] = useState<UserPublic | null>(null);
  const [passwordUser, setPasswordUser] = useState<UserPublic | null>(null);
  const [confirmModal, setConfirmModal] = useState<{
    type: 'deactivate' | 'demote';
    targetUser: UserPublic;
  } | null>(null);

  // Form states inside modals
  const [createEmail, setCreateEmail] = useState('');
  const [createRole, setCreateRole] = useState<'user' | 'admin'>('user');
  const [createPassword, setCreatePassword] = useState('');
  const [createConfirmPassword, setCreateConfirmPassword] = useState('');
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const [editEmail, setEditEmail] = useState('');
  const [editRole, setEditRole] = useState<'user' | 'admin'>('user');
  const [editIsActive, setEditIsActive] = useState<boolean>(true);
  const [editError, setEditError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const loadUsers = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await usersApi.listUsers();
      setUsers(data.users);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setError(
        err instanceof Error ? err.message : 'Error al cargar la lista de usuarios'
      );
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const formatDate = (isoString?: string | null): string => {
    if (!isoString) return 'Nunca';
    try {
      const date = new Date(isoString);
      return new Intl.DateTimeFormat('es-ES', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date);
    } catch {
      return isoString;
    }
  };

  // --- Handlers para CREAR ---
  const handleOpenCreateModal = () => {
    setCreateEmail('');
    setCreateRole('user');
    setCreatePassword('');
    setCreateConfirmPassword('');
    setCreateError(null);
    setShowCreateModal(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    if (!createEmail.trim()) {
      setCreateError('El correo electrónico es obligatorio.');
      return;
    }
    if (createPassword.length < 12) {
      setCreateError('La contraseña debe tener al menos 12 caracteres.');
      return;
    }
    if (createPassword !== createConfirmPassword) {
      setCreateError('Las contraseñas no coinciden.');
      return;
    }

    setIsCreating(true);
    try {
      const newUser = await usersApi.createUser({
        email: createEmail.trim(),
        role: createRole,
        password: createPassword,
        confirm_password: createConfirmPassword,
      });
      setUsers((prev) => [newUser, ...prev]);
      setShowCreateModal(false);
      setSuccessMsg(`Usuario ${newUser.email} creado correctamente.`);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setCreateError(
        err instanceof Error ? err.message : 'Error al crear el usuario.'
      );
    } finally {
      setIsCreating(false);
    }
  };

  // --- Handlers para EDITAR ---
  const handleOpenEditModal = (target: UserPublic) => {
    setEditingUser(target);
    setEditEmail(target.email);
    setEditRole(target.role as 'user' | 'admin');
    setEditIsActive(target.is_active);
    setEditError(null);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingUser) return;
    setEditError(null);

    const isDemotingSelf =
      editingUser.id === currentUser?.id &&
      editingUser.role === 'admin' &&
      editRole === 'user';

    const isDeactivatingSelf =
      editingUser.id === currentUser?.id &&
      editingUser.is_active &&
      !editIsActive;

    // Si requiere confirmación especial (auto-degradación o auto-desactivación)
    if (isDemotingSelf) {
      setConfirmModal({ type: 'demote', targetUser: editingUser });
      return;
    }
    if (isDeactivatingSelf) {
      setConfirmModal({ type: 'deactivate', targetUser: editingUser });
      return;
    }

    await executeUpdate(editingUser.id, {
      email: editEmail !== editingUser.email ? editEmail.trim() : undefined,
      role: editRole !== editingUser.role ? editRole : undefined,
      is_active: editIsActive !== editingUser.is_active ? editIsActive : undefined,
    });
  };

  const executeUpdate = async (
    targetId: string,
    payload: usersApi.UserUpdatePayload
  ) => {
    setIsEditing(true);
    try {
      const updated = await usersApi.updateUser(targetId, payload);
      setUsers((prev) => prev.map((u) => (u.id === targetId ? updated : u)));
      setEditingUser(null);
      setConfirmModal(null);

      // Si el usuario editó sus propios datos
      if (currentUser && targetId === currentUser.id) {
        if (!updated.is_active) {
          await logout();
          return;
        }
        updateCurrentUser({
          email: updated.email,
          role: updated.role,
          is_active: updated.is_active,
        });
      }

      setSuccessMsg(`Usuario ${updated.email} actualizado exitosamente.`);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setEditError(
        err instanceof Error ? err.message : 'Error al actualizar el usuario.'
      );
    } finally {
      setIsEditing(false);
    }
  };

  // --- Handlers para CAMBIAR CONTRASEÑA ---
  const handleOpenPasswordModal = (target: UserPublic) => {
    setPasswordUser(target);
    setNewPassword('');
    setConfirmNewPassword('');
    setPasswordError(null);
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passwordUser) return;
    setPasswordError(null);

    if (newPassword.length < 12) {
      setPasswordError('La nueva contraseña debe tener al menos 12 caracteres.');
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setPasswordError('Las contraseñas no coinciden.');
      return;
    }

    setIsChangingPassword(true);
    try {
      await usersApi.changeUserPassword(passwordUser.id, {
        password: newPassword,
        confirm_password: confirmNewPassword,
      });

      setPasswordUser(null);

      // Si el admin cambió su propia contraseña, su sesión ha sido revocada
      if (currentUser && passwordUser.id === currentUser.id) {
        await logout();
        return;
      }

      setSuccessMsg(
        `Contraseña de ${passwordUser.email} restablecida correctamente. Todas sus sesiones activas han sido revocadas.`
      );
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setPasswordError(
        err instanceof Error
          ? err.message
          : 'Error al cambiar la contraseña del usuario.'
      );
    } finally {
      setIsChangingPassword(false);
    }
  };

  // --- Handlers para ACTIVAR / DESACTIVAR directo ---
  const handleToggleActiveClick = (target: UserPublic) => {
    if (target.is_active) {
      // Confirmar desactivación
      setConfirmModal({ type: 'deactivate', targetUser: target });
    } else {
      // Activar directo
      executeUpdate(target.id, { is_active: true });
    }
  };

  return (
    <div className="users-management-container">
      {/* Cabecera de la sección Configuración -> Usuarios */}
      <div className="users-header">
        <div>
          <div className="users-breadcrumb">
            <span>Configuración</span>
            <span className="breadcrumb-separator">/</span>
            <span className="breadcrumb-current">Usuarios</span>
          </div>
          <h2 className="users-title">Gestión de Cuentas y Accesos</h2>
          <p className="users-subtitle">
            Administre los usuarios habilitados para acceder a HITCHINGS Y GONZALEZ DOCUMENTOS.
          </p>
        </div>

        <button
          type="button"
          className="btn-primary users-new-btn"
          onClick={handleOpenCreateModal}
        >
          <UserPlus size={16} />
          <span>Nuevo usuario</span>
        </button>
      </div>

      {/* Alertas de Éxito / Error general */}
      {successMsg && (
        <div className="banner banner-success" role="status">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle2 size={18} />
            <span>{successMsg}</span>
          </div>
          <button
            type="button"
            className="btn-secondary-sm"
            onClick={() => setSuccessMsg(null)}
          >
            Cerrar
          </button>
        </div>
      )}

      {error && (
        <div className="banner banner-danger" role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="banner-retry-btn"
            onClick={loadUsers}
          >
            <RefreshCw size={14} />
            Reintentar
          </button>
        </div>
      )}

      {/* Tabla de Usuarios */}
      <div className="users-table-card">
        {isLoading ? (
          <div className="users-loading-state" role="status">
            <Loader2 className="auth-loading-spinner" size={28} />
            <p>Cargando usuarios del sistema...</p>
          </div>
        ) : users.length === 0 ? (
          <div className="users-empty-state">
            <Users size={40} className="empty-icon" />
            <p>No se encontraron usuarios registrados.</p>
          </div>
        ) : (
          <div className="users-table-responsive">
            <table className="users-table">
              <thead>
                <tr>
                  <th>Correo electrónico</th>
                  <th>Rol</th>
                  <th>Estado</th>
                  <th>Fecha de alta</th>
                  <th>Último acceso</th>
                  <th style={{ textAlign: 'right' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => {
                  const isSelf = currentUser?.id === u.id;
                  return (
                    <tr key={u.id} className={!u.is_active ? 'row-inactive' : ''}>
                      <td>
                        <div className="user-email-cell">
                          <span className="user-email-text">{u.email}</span>
                          {isSelf && <span className="badge-self">Tú</span>}
                        </div>
                      </td>
                      <td>
                        {u.role === 'admin' ? (
                          <span className="role-badge role-admin">
                            <Shield size={12} />
                            Administrador
                          </span>
                        ) : (
                          <span className="role-badge role-user">
                            Usuario
                          </span>
                        )}
                      </td>
                      <td>
                        {u.is_active ? (
                          <span className="status-badge status-active">
                            <UserCheck size={12} />
                            Activo
                          </span>
                        ) : (
                          <span className="status-badge status-inactive">
                            <UserX size={12} />
                            Inactivo
                          </span>
                        )}
                      </td>
                      <td>
                        <span className="user-date-text">{formatDate(u.created_at)}</span>
                      </td>
                      <td>
                        <span className="user-date-text">{formatDate(u.last_login_at)}</span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="users-actions-group">
                          <button
                            type="button"
                            className="btn-action-icon"
                            onClick={() => handleOpenEditModal(u)}
                            title="Editar usuario"
                            aria-label={`Editar a ${u.email}`}
                          >
                            <Edit2 size={14} />
                            <span>Editar</span>
                          </button>
                          <button
                            type="button"
                            className="btn-action-icon"
                            onClick={() => handleOpenPasswordModal(u)}
                            title="Restablecer contraseña"
                            aria-label={`Cambiar contraseña de ${u.email}`}
                          >
                            <KeyRound size={14} />
                            <span>Clave</span>
                          </button>
                          <button
                            type="button"
                            className={`btn-action-icon ${
                              u.is_active ? 'btn-action-danger' : 'btn-action-success'
                            }`}
                            onClick={() => handleToggleActiveClick(u)}
                            title={u.is_active ? 'Desactivar usuario' : 'Activar usuario'}
                            aria-label={
                              u.is_active
                                ? `Desactivar a ${u.email}`
                                : `Activar a ${u.email}`
                            }
                          >
                            {u.is_active ? (
                              <>
                                <UserX size={14} />
                                <span>Desactivar</span>
                              </>
                            ) : (
                              <>
                                <UserCheck size={14} />
                                <span>Activar</span>
                              </>
                            )}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* MODAL 1: CREAR NUEVO USUARIO */}
      {showCreateModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-container">
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserPlus size={18} color="#0f2b48" />
                <h3 className="modal-title">Nuevo usuario</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowCreateModal(false)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit}>
              <div className="modal-body">
                {createError && (
                  <div className="banner banner-danger banner-modal" role="alert">
                    <AlertCircle size={16} />
                    <span>{createError}</span>
                  </div>
                )}

                <div className="form-field">
                  <label htmlFor="create-email" className="field-label">
                    Correo electrónico
                  </label>
                  <input
                    id="create-email"
                    type="email"
                    className="custom-input"
                    value={createEmail}
                    onChange={(e) => setCreateEmail(e.target.value)}
                    placeholder="ejemplo@hitchings-gonzalez.com"
                    required
                    autoFocus
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="create-role" className="field-label">
                    Rol asignado
                  </label>
                  <select
                    id="create-role"
                    className="custom-select"
                    value={createRole}
                    onChange={(e) => setCreateRole(e.target.value as 'user' | 'admin')}
                  >
                    <option value="user">Usuario</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>

                <div className="form-field">
                  <label htmlFor="create-password" className="field-label">
                    Contraseña inicial
                  </label>
                  <input
                    id="create-password"
                    type="password"
                    className="custom-input"
                    value={createPassword}
                    onChange={(e) => setCreatePassword(e.target.value)}
                    placeholder="Mínimo 12 caracteres"
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="create-confirm-password" className="field-label">
                    Confirmar contraseña
                  </label>
                  <input
                    id="create-confirm-password"
                    type="password"
                    className="custom-input"
                    value={createConfirmPassword}
                    onChange={(e) => setCreateConfirmPassword(e.target.value)}
                    placeholder="Repita la contraseña"
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateModal(false)}
                  disabled={isCreating}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isCreating}
                >
                  {isCreating ? 'Guardando...' : 'Crear usuario'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: EDITAR USUARIO */}
      {editingUser && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-container">
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Edit2 size={18} color="#0f2b48" />
                <h3 className="modal-title">Editar usuario</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setEditingUser(null)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit}>
              <div className="modal-body">
                {editError && (
                  <div className="banner banner-danger banner-modal" role="alert">
                    <AlertCircle size={16} />
                    <span>{editError}</span>
                  </div>
                )}

                <div className="form-field">
                  <label htmlFor="edit-email" className="field-label">
                    Correo electrónico
                  </label>
                  <input
                    id="edit-email"
                    type="email"
                    className="custom-input"
                    value={editEmail}
                    onChange={(e) => setEditEmail(e.target.value)}
                    required
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="edit-role" className="field-label">
                    Rol
                  </label>
                  <select
                    id="edit-role"
                    className="custom-select"
                    value={editRole}
                    onChange={(e) => setEditRole(e.target.value as 'user' | 'admin')}
                  >
                    <option value="user">Usuario</option>
                    <option value="admin">Administrador</option>
                  </select>
                </div>

                <div className="form-field">
                  <label htmlFor="edit-status" className="field-label">
                    Estado de la cuenta
                  </label>
                  <select
                    id="edit-status"
                    className="custom-select"
                    value={editIsActive ? 'active' : 'inactive'}
                    onChange={(e) => setEditIsActive(e.target.value === 'active')}
                  >
                    <option value="active">Activo</option>
                    <option value="inactive">Inactivo</option>
                  </select>
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setEditingUser(null)}
                  disabled={isEditing}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isEditing}
                >
                  {isEditing ? 'Guardando...' : 'Guardar cambios'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: RESTABLECER CONTRASEÑA */}
      {passwordUser && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-container">
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <KeyRound size={18} color="#0f2b48" />
                <h3 className="modal-title">Restablecer contraseña</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setPasswordUser(null)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handlePasswordSubmit}>
              <div className="modal-body">
                <p className="modal-info-text">
                  Usuario: <strong>{passwordUser.email}</strong>
                </p>
                <p className="modal-warning-text">
                  Nota: Al establecer una nueva contraseña se revocarán inmediatamente
                  todas las sesiones activas asociadas a este usuario.
                </p>

                {passwordError && (
                  <div className="banner banner-danger banner-modal" role="alert">
                    <AlertCircle size={16} />
                    <span>{passwordError}</span>
                  </div>
                )}

                <div className="form-field">
                  <label htmlFor="new-password" className="field-label">
                    Nueva contraseña
                  </label>
                  <input
                    id="new-password"
                    type="password"
                    className="custom-input"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Mínimo 12 caracteres"
                    minLength={12}
                    maxLength={128}
                    required
                    autoFocus
                  />
                </div>

                <div className="form-field">
                  <label htmlFor="confirm-new-password" className="field-label">
                    Confirmar nueva contraseña
                  </label>
                  <input
                    id="confirm-new-password"
                    type="password"
                    className="custom-input"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    placeholder="Repita la nueva contraseña"
                    minLength={12}
                    maxLength={128}
                    required
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setPasswordUser(null)}
                  disabled={isChangingPassword}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isChangingPassword}
                >
                  {isChangingPassword ? 'Actualizando...' : 'Actualizar contraseña'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 4: CONFIRMACIÓN DE ACCIONES CRÍTICAS */}
      {confirmModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-container modal-danger">
            <div className="modal-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <AlertTriangle size={20} color="#dc2626" />
                <h3 className="modal-title" style={{ color: '#991b1b' }}>
                  {confirmModal.type === 'deactivate'
                    ? 'Confirmar desactivación de usuario'
                    : 'Confirmar degradación de rol'}
                </h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setConfirmModal(null)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <div className="modal-body">
              <p style={{ fontSize: '0.95rem', color: '#334155', marginBottom: '0.75rem' }}>
                ¿Está seguro de que desea proceder sobre la cuenta{' '}
                <strong>{confirmModal.targetUser.email}</strong>?
              </p>

              {confirmModal.type === 'deactivate' ? (
                <p className="modal-warning-text">
                  Esta acción revocará inmediatamente todas las sesiones activas del
                  usuario. No podrá volver a iniciar sesión hasta que un administrador
                  reactive su cuenta.
                </p>
              ) : (
                <p className="modal-warning-text">
                  El usuario perderá inmediatamente todos los privilegios administrativos
                  y no podrá gestionar cuentas del despacho.
                </p>
              )}

              {confirmModal.targetUser.id === currentUser?.id && (
                <div className="banner banner-danger banner-modal" style={{ marginTop: '0.75rem' }}>
                  <AlertCircle size={16} />
                  <span>
                    Atención: Estás modificando tu propia cuenta. Tu sesión actual se
                    cerrará o tus privilegios cambiarán en el acto.
                  </span>
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setConfirmModal(null)}
                disabled={isEditing}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn-danger"
                disabled={isEditing}
                onClick={() => {
                  if (confirmModal.type === 'deactivate') {
                    executeUpdate(confirmModal.targetUser.id, { is_active: false });
                  } else {
                    executeUpdate(confirmModal.targetUser.id, { role: 'user' });
                  }
                }}
              >
                {isEditing ? 'Procesando...' : 'Confirmar'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
