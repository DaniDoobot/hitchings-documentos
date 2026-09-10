import React, { useState, useEffect, useCallback } from 'react';
import {
  FileCode2,
  Plus,
  Edit2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  AlertCircle,
  X,
  Loader2,
  ShieldCheck,
  Power,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import * as analysisTypesApi from '../api/analysisTypes';
import { ApiError } from '../api/client';
import type { AnalysisType } from '../types/analysisTypes';

interface AnalysisTypesManagementProps {
  onTypesUpdated?: () => void;
}

export const AnalysisTypesManagement: React.FC<AnalysisTypesManagementProps> = ({
  onTypesUpdated,
}) => {
  const { logout } = useAuth();

  const [types, setTypes] = useState<AnalysisType[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [editingType, setEditingType] = useState<AnalysisType | null>(null);

  // Form states - Create
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createInstructions, setCreateInstructions] = useState('');
  const [createIsActive, setCreateIsActive] = useState<boolean>(true);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Form states - Edit
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editInstructions, setEditInstructions] = useState('');
  const [editIsActive, setEditIsActive] = useState<boolean>(true);
  const [editError, setEditError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);

  const loadTypes = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await analysisTypesApi.listAnalysisTypes(true);
      setTypes(data.items);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setError(
        err instanceof Error ? err.message : 'Error al cargar los tipos de análisis'
      );
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    loadTypes();
  }, [loadTypes]);

  const handleOpenCreateModal = () => {
    setCreateName('');
    setCreateDescription('');
    setCreateInstructions('');
    setCreateIsActive(true);
    setCreateError(null);
    setShowCreateModal(true);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    const nameTrim = createName.trim();
    if (nameTrim.length < 2 || nameTrim.length > 150) {
      setCreateError('El nombre debe tener entre 2 y 150 caracteres.');
      return;
    }

    const instTrim = createInstructions.trim();
    if (instTrim.length < 10) {
      setCreateError('Las instrucciones especializadas deben tener al menos 10 caracteres.');
      return;
    }

    setIsCreating(true);
    try {
      await analysisTypesApi.createAnalysisType({
        name: nameTrim,
        description: createDescription.trim(),
        instructions: instTrim,
        is_active: createIsActive,
      });

      setSuccessMsg(`Tipo de análisis "${nameTrim}" creado correctamente.`);
      setShowCreateModal(false);
      await loadTypes();
      if (onTypesUpdated) {
        onTypesUpdated();
      }
    } catch (err) {
      setCreateError(
        err instanceof Error ? err.message : 'Error al crear el tipo de análisis'
      );
    } finally {
      setIsCreating(false);
    }
  };

  const handleOpenEditModal = (item: AnalysisType) => {
    setEditingType(item);
    setEditName(item.name);
    setEditDescription(item.description);
    setEditInstructions(item.instructions);
    setEditIsActive(item.is_active);
    setEditError(null);
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingType) return;
    setEditError(null);

    const nameTrim = editName.trim();
    if (nameTrim.length < 2 || nameTrim.length > 150) {
      setEditError('El nombre debe tener entre 2 y 150 caracteres.');
      return;
    }

    const instTrim = editInstructions.trim();
    if (instTrim.length < 10) {
      setEditError('Las instrucciones especializadas deben tener al menos 10 caracteres.');
      return;
    }

    setIsEditing(true);
    try {
      await analysisTypesApi.updateAnalysisType(editingType.id, {
        name: nameTrim,
        description: editDescription.trim(),
        instructions: instTrim,
        is_active: editIsActive,
      });

      setSuccessMsg(`Tipo de análisis "${nameTrim}" actualizado correctamente.`);
      setEditingType(null);
      await loadTypes();
      if (onTypesUpdated) {
        onTypesUpdated();
      }
    } catch (err) {
      setEditError(
        err instanceof Error ? err.message : 'Error al actualizar el tipo de análisis'
      );
    } finally {
      setIsEditing(false);
    }
  };

  const handleToggleActive = async (item: AnalysisType) => {
    const newState = !item.is_active;
    try {
      await analysisTypesApi.updateAnalysisType(item.id, {
        is_active: newState,
      });
      setSuccessMsg(
        `Tipo "${item.name}" ${newState ? 'activado' : 'desactivado'} correctamente.`
      );
      await loadTypes();
      if (onTypesUpdated) {
        onTypesUpdated();
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Error al cambiar el estado del tipo de análisis'
      );
    }
  };

  return (
    <div className="users-management">
      {/* Base Estructural Jurídica Callout */}
      <div className="banner banner-info structural-prompt-banner" role="region" aria-label="Base Estructural Jurídica">
        <div className="structural-banner-content">
          <ShieldCheck size={20} className="structural-banner-icon" />
          <div>
            <h4 className="structural-banner-title">
              Base Estructural Jurídica de HITCHINGS & GONZÁLEZ (Inmutable)
            </h4>
            <p className="structural-banner-text">
              Todo tipo de análisis se ejecuta integrado con las directivas procesales y deontológicas de máxima prioridad del despacho:
              rigor probatorio, especialización en Derecho de la Competencia (antitrust), Derecho de la Unión Europea y acciones colectivas,
              estricta separación epistémica de hechos y alegaciones, e inmunidad absoluta ante inyección de instrucciones en los documentos.
              Las plantillas a continuación configuran el enfoque especializado y temático de cada análisis.
            </p>
          </div>
        </div>
      </div>

      {/* Header y Acciones */}
      <div className="users-header">
        <div className="users-title-group">
          <div className="users-icon-badge">
            <FileCode2 size={24} />
          </div>
          <div>
            <h2 className="users-title">Tipos de análisis documental</h2>
            <p className="users-subtitle">
              Catálogo compartido para todo el despacho ({types.length} registrados)
            </p>
          </div>
        </div>

        <div className="users-actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={loadTypes}
            disabled={isLoading}
            title="Recargar listado"
            aria-label="Recargar listado de tipos de análisis"
          >
            <RefreshCw size={16} className={isLoading ? 'spin-icon' : ''} />
            <span>Actualizar</span>
          </button>

          <button
            type="button"
            className="btn-primary"
            onClick={handleOpenCreateModal}
            aria-label="Crear nuevo tipo de análisis"
          >
            <Plus size={16} />
            <span>Nuevo tipo</span>
          </button>
        </div>
      </div>

      {/* Mensajes de error y éxito */}
      {error && (
        <div className="banner banner-danger" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
          <button
            type="button"
            className="btn-secondary-sm"
            onClick={() => setError(null)}
          >
            Cerrar
          </button>
        </div>
      )}

      {successMsg && (
        <div className="banner banner-success" role="status">
          <CheckCircle2 size={18} />
          <span>{successMsg}</span>
          <button
            type="button"
            className="btn-secondary-sm"
            onClick={() => setSuccessMsg(null)}
          >
            Cerrar
          </button>
        </div>
      )}

      {/* Tabla de Tipos de Análisis */}
      <div className="users-table-container">
        {isLoading && types.length === 0 ? (
          <div className="users-loading-state" role="status">
            <Loader2 size={32} className="spin-icon" />
            <p>Cargando catálogo de tipos de análisis...</p>
          </div>
        ) : (
          <table className="users-table" aria-label="Tipos de análisis disponibles">
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Código (Identificador)</th>
                <th>Descripción</th>
                <th>Estado</th>
                <th className="th-actions">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {types.map((item) => (
                <tr key={item.id} className={!item.is_active ? 'row-inactive' : ''}>
                  <td className="cell-primary font-semibold">{item.name}</td>
                  <td>
                    <code className="code-badge">{item.code}</code>
                  </td>
                  <td className="cell-secondary">{item.description || '—'}</td>
                  <td>
                    {item.is_active ? (
                      <span className="badge badge-success">
                        <CheckCircle2 size={12} />
                        <span>Activo</span>
                      </span>
                    ) : (
                      <span className="badge badge-inactive">
                        <XCircle size={12} />
                        <span>Inactivo</span>
                      </span>
                    )}
                  </td>
                  <td className="cell-actions">
                    <button
                      type="button"
                      className="btn-icon"
                      onClick={() => handleOpenEditModal(item)}
                      title={`Editar ${item.name}`}
                      aria-label={`Editar ${item.name}`}
                    >
                      <Edit2 size={15} />
                    </button>
                    <button
                      type="button"
                      className={`btn-icon ${item.is_active ? 'btn-icon-warning' : 'btn-icon-success'}`}
                      onClick={() => handleToggleActive(item)}
                      title={item.is_active ? `Desactivar ${item.name}` : `Activar ${item.name}`}
                      aria-label={item.is_active ? `Desactivar ${item.name}` : `Activar ${item.name}`}
                    >
                      <Power size={15} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal: CREAR TIPO */}
      {showCreateModal && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-create-type-title">
          <div className="modal-card modal-lg">
            <div className="modal-header">
              <h3 id="modal-create-type-title" className="modal-title">
                Nuevo tipo de análisis
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowCreateModal(false)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="modal-form">
              {createError && (
                <div className="banner banner-danger" role="alert">
                  <AlertCircle size={16} />
                  <span>{createError}</span>
                </div>
              )}

              <div className="form-group">
                <label htmlFor="create-type-name" className="form-label">
                  Nombre del tipo de análisis <span className="required-star">*</span>
                </label>
                <input
                  id="create-type-name"
                  type="text"
                  className="form-input"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder="Ej: Análisis de Cárteles y Fijación de Precios"
                  required
                  maxLength={150}
                  autoFocus
                />
                <span className="form-hint">
                  El código identificador único (slug) se generará automáticamente a partir del nombre y será inmutable.
                </span>
              </div>

              <div className="form-group">
                <label htmlFor="create-type-description" className="form-label">
                  Descripción breve
                </label>
                <input
                  id="create-type-description"
                  type="text"
                  className="form-input"
                  value={createDescription}
                  onChange={(e) => setCreateDescription(e.target.value)}
                  placeholder="Finalidad y alcance de este análisis"
                  maxLength={1000}
                />
              </div>

              <div className="form-group">
                <label htmlFor="create-type-instructions" className="form-label">
                  Instrucciones especializadas del modelo <span className="required-star">*</span>
                </label>
                <textarea
                  id="create-type-instructions"
                  className="form-textarea form-textarea-large"
                  rows={8}
                  value={createInstructions}
                  onChange={(e) => setCreateInstructions(e.target.value)}
                  placeholder="Pautas detalladas, estructura de apartados y reglas de análisis..."
                  required
                />
                <span className="form-hint">
                  Mínimo 10 caracteres. Se concatenará de forma subordinada a la Base Estructural Jurídica de la firma.
                </span>
              </div>

              <div className="form-group-checkbox">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={createIsActive}
                    onChange={(e) => setCreateIsActive(e.target.checked)}
                  />
                  <span>Activo (disponible inmediatamente en el selector de análisis)</span>
                </label>
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
                  {isCreating ? (
                    <>
                      <Loader2 size={16} className="spin-icon" />
                      <span>Creando...</span>
                    </>
                  ) : (
                    <span>Crear tipo de análisis</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: EDITAR TIPO */}
      {editingType && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-edit-type-title">
          <div className="modal-card modal-lg">
            <div className="modal-header">
              <h3 id="modal-edit-type-title" className="modal-title">
                Editar tipo de análisis
              </h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setEditingType(null)}
                aria-label="Cerrar modal"
              >
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleEditSubmit} className="modal-form">
              {editError && (
                <div className="banner banner-danger" role="alert">
                  <AlertCircle size={16} />
                  <span>{editError}</span>
                </div>
              )}

              <div className="form-group">
                <label className="form-label">
                  Código identificador estable
                </label>
                <div className="form-static-code">
                  <code className="code-badge">{editingType.code}</code>
                  <span className="form-hint-inline">Inmutable (preserva referencias de ejecución)</span>
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="edit-type-name" className="form-label">
                  Nombre <span className="required-star">*</span>
                </label>
                <input
                  id="edit-type-name"
                  type="text"
                  className="form-input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  required
                  maxLength={150}
                />
              </div>

              <div className="form-group">
                <label htmlFor="edit-type-description" className="form-label">
                  Descripción
                </label>
                <input
                  id="edit-type-description"
                  type="text"
                  className="form-input"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  maxLength={1000}
                />
              </div>

              <div className="form-group">
                <label htmlFor="edit-type-instructions" className="form-label">
                  Instrucciones especializadas <span className="required-star">*</span>
                </label>
                <textarea
                  id="edit-type-instructions"
                  className="form-textarea form-textarea-large"
                  rows={8}
                  value={editInstructions}
                  onChange={(e) => setEditInstructions(e.target.value)}
                  required
                />
              </div>

              <div className="form-group-checkbox">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={editIsActive}
                    onChange={(e) => setEditIsActive(e.target.checked)}
                  />
                  <span>Activo (disponible en el selector de análisis)</span>
                </label>
              </div>

              <div className="modal-footer">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setEditingType(null)}
                  disabled={isEditing}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={isEditing}
                >
                  {isEditing ? (
                    <>
                      <Loader2 size={16} className="spin-icon" />
                      <span>Guardando...</span>
                    </>
                  ) : (
                    <span>Guardar cambios</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
