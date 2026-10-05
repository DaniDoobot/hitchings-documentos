import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Save,
  AlertCircle,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Clock,
  User,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import * as promptSettingsApi from '../api/promptSettings';
import { ApiError } from '../api/client';
import type { PromptSetting } from '../types/promptSettings';

export const BasePromptManagement: React.FC = () => {
  const { logout } = useAuth();
  const [promptSetting, setPromptSetting] = useState<PromptSetting | null>(null);
  const [content, setContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadBasePrompt = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await promptSettingsApi.getBasePrompt();
      setPromptSetting(data);
      setContent(data.content);
      setOriginalContent(data.content);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Error al cargar el Prompt Base');
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    loadBasePrompt();
  }, [loadBasePrompt]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    const trimmed = content.trim();
    if (trimmed.length < 10) {
      setError('El Prompt base no puede estar vacío y debe contener al menos 10 caracteres.');
      return;
    }
    if (trimmed.length > 30000) {
      setError('El contenido supera el límite máximo permitido de 30.000 caracteres.');
      return;
    }

    setIsSaving(true);
    try {
      const updated = await promptSettingsApi.updateBasePrompt(trimmed);
      setPromptSetting(updated);
      setContent(updated.content);
      setOriginalContent(updated.content);
      setSuccessMsg('Prompt Base global guardado correctamente. Los cambios se aplicarán inmediatamente a todos los análisis.');
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        await logout();
        return;
      }
      setError(err instanceof Error ? err.message : 'Error al guardar el Prompt Base');
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = () => {
    setContent(originalContent);
    setError(null);
    setSuccessMsg(null);
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleString('es-ES', {
        dateStyle: 'medium',
        timeStyle: 'short',
      });
    } catch {
      return isoString;
    }
  };

  const hasChanges = content !== originalContent;

  return (
    <div className="users-card" aria-label="Gestión del Prompt Base Global">
      <div className="users-card-header">
        <div>
          <h2 className="users-card-title">
            <FileText size={20} color="#0f2b48" />
            Prompt Base Global
          </h2>
          <p className="users-card-desc">
            Este prompt se aplica como contexto general a todos los análisis antes de las instrucciones específicas de cada Tipo de análisis.
          </p>
        </div>
        <button
          type="button"
          className="btn-secondary"
          onClick={loadBasePrompt}
          disabled={isLoading || isSaving}
          title="Recargar Prompt Base"
          aria-label="Recargar Prompt Base"
        >
          <RefreshCw size={14} className={isLoading ? 'spin-icon' : ''} />
          <span>Recargar</span>
        </button>
      </div>

      <div className="banner banner-warning" style={{ margin: '1rem 0', display: 'flex', gap: '0.6rem', alignItems: 'center' }}>
        <AlertTriangle size={18} color="#b45309" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: '0.85rem', color: '#92400e' }}>
          <strong>Aviso:</strong> Los cambios que guardes en el Prompt Base afectan de inmediato a todos los usuarios del despacho y a todos los Tipos de análisis.
        </span>
      </div>

      {error && (
        <div className="banner banner-danger" role="alert" style={{ marginBottom: '1rem' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="banner banner-success" role="status" style={{ marginBottom: '1rem' }}>
          <CheckCircle2 size={16} />
          <span>{successMsg}</span>
        </div>
      )}

      {isLoading ? (
        <div className="users-loading-state" role="status" aria-label="Cargando configuración">
          <Loader2 className="users-loading-spinner" size={28} />
          <p>Cargando Prompt Base global desde la base de datos...</p>
        </div>
      ) : (
        <form onSubmit={handleSave} className="base-prompt-form">
          <div className="form-field">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
              <label htmlFor="base-prompt-content" className="field-label" style={{ marginBottom: 0 }}>
                Contenido sustantivo del Prompt Base <span className="required-star">*</span>
              </label>
              <span style={{ fontSize: '0.75rem', color: content.length > 29000 ? '#b91c1c' : '#64748b' }}>
                {content.length.toLocaleString()} / 30.000 caracteres
              </span>
            </div>
            <textarea
              id="base-prompt-content"
              className="custom-textarea form-textarea-large"
              style={{
                fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                fontSize: '0.84rem',
                minHeight: '380px',
                lineHeight: 1.5,
              }}
              rows={16}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Escribe las directivas y criterios jurídicos base aplicables a todos los análisis..."
              required
            />
            <span className="field-help">
              Puedes ajustar con total libertad los criterios del despacho, reglas probatorias, advertencias y directivas procesales.
            </span>
          </div>

          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '1rem',
              marginTop: '1.25rem',
              paddingTop: '1rem',
              borderTop: '1px solid var(--border-color)',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.25rem', fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <Clock size={14} color="#64748b" />
                <span>Última modificación: <strong>{formatDate(promptSetting?.updated_at)}</strong></span>
              </div>
              {promptSetting?.updated_by_email && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                  <User size={14} color="#64748b" />
                  <span>Modificado por: <strong>{promptSetting.updated_by_email}</strong></span>
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button
                type="button"
                className="btn-secondary"
                onClick={handleReset}
                disabled={!hasChanges || isSaving}
              >
                Descartar cambios
              </button>
              <button
                type="submit"
                className="btn-primary"
                disabled={!hasChanges || isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 size={16} className="spin-icon" />
                    <span>Guardando...</span>
                  </>
                ) : (
                  <>
                    <Save size={16} />
                    <span>Guardar cambios</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </form>
      )}
    </div>
  );
};
