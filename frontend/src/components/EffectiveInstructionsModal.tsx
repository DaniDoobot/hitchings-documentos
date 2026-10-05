import React, { useState, useEffect } from 'react';
import {
  FileText,
  X,
  Loader2,
  AlertCircle,
  Copy,
  Check,
  Layers,
  Sparkles,
} from 'lucide-react';
import * as promptSettingsApi from '../api/promptSettings';
import type { EffectiveInstructionsResponse } from '../types/promptSettings';
import type { DetailLevel, OutputFormat } from '../types/api';

interface EffectiveInstructionsModalProps {
  isOpen: boolean;
  onClose: () => void;
  selectedPromptId: string;
  detailLevel: DetailLevel;
  outputFormat: OutputFormat;
  additionalInstructions?: string;
}

export const EffectiveInstructionsModal: React.FC<EffectiveInstructionsModalProps> = ({
  isOpen,
  onClose,
  selectedPromptId,
  detailLevel,
  outputFormat,
  additionalInstructions,
}) => {
  const [data, setData] = useState<EffectiveInstructionsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'breakdown' | 'integrated'>('breakdown');

  useEffect(() => {
    if (!isOpen || !selectedPromptId) {
      setData(null);
      setError(null);
      return;
    }

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    promptSettingsApi
      .previewEffectiveInstructions({
        prompt_id: selectedPromptId,
        detail_level: detailLevel,
        output_format: outputFormat,
        additional_instructions: additionalInstructions?.trim() || undefined,
      })
      .then((res) => {
        if (isMounted) {
          setData(res);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Error al obtener la descomposición de instrucciones.'
          );
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [isOpen, selectedPromptId, detailLevel, outputFormat, additionalInstructions]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopy = async (text: string, sectionKey: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(sectionKey);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch {
      // Fallback si clipboard falla
    }
  };

  return (
    <div
      className="modal-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-effective-instructions-title"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="modal-container modal-xl effective-instructions-modal">
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={20} color="#2563eb" />
            <div>
              <h3 id="modal-effective-instructions-title" className="modal-title">
                Instrucciones Utilizadas para el Análisis
              </h3>
              <p className="modal-subtitle-sm">
                Transparencia de las directivas intelectuales enviadas a la inteligencia artificial
              </p>
            </div>
          </div>
          <button
            type="button"
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Cerrar modal"
          >
            <X size={18} />
          </button>
        </div>

        <div className="modal-body effective-instructions-body">
          {error && (
            <div className="banner banner-danger banner-modal" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          {isLoading ? (
            <div className="instructions-loading-state" role="status" aria-label="Cargando instrucciones">
              <Loader2 className="users-loading-spinner" size={32} />
              <p>Componiendo desglose transparente de instrucciones...</p>
            </div>
          ) : data ? (
            <>
              {/* Selector de modo: Desglose por capas vs Integrado */}
              <div className="instructions-tabs-bar">
                <div className="instructions-segmented-control">
                  <button
                    type="button"
                    className={`instruction-tab-btn ${viewMode === 'breakdown' ? 'active' : ''}`}
                    onClick={() => setViewMode('breakdown')}
                  >
                    <Layers size={14} />
                    <span>Desglose por capas (5 componentes)</span>
                  </button>
                  <button
                    type="button"
                    className={`instruction-tab-btn ${viewMode === 'integrated' ? 'active' : ''}`}
                    onClick={() => setViewMode('integrated')}
                  >
                    <FileText size={14} />
                    <span>Prompt completo integrado</span>
                  </button>
                </div>

                <button
                  type="button"
                  className="btn-secondary-sm copy-all-btn"
                  onClick={() => handleCopy(data.effective_full_prompt, 'all')}
                  title="Copiar prompt completo integrado"
                >
                  {copiedSection === 'all' ? (
                    <>
                      <Check size={13} color="#16a34a" />
                      <span>¡Copiado!</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copiar prompt completo</span>
                    </>
                  )}
                </button>
              </div>

              {viewMode === 'breakdown' ? (
                <div className="instructions-breakdown-list">
                  {/* Capa 1: Prompt Base Global */}
                  <div className="instruction-layer-card">
                    <div className="instruction-layer-header">
                      <div className="instruction-layer-badge-wrap">
                        <span className="preview-order-badge">1</span>
                        <h4 className="instruction-layer-title">Prompt Base Global del Despacho</h4>
                      </div>
                      <button
                        type="button"
                        className="btn-icon-copy"
                        onClick={() => handleCopy(data.base_prompt, 'base')}
                        title="Copiar Prompt Base"
                        aria-label="Copiar Prompt Base"
                      >
                        {copiedSection === 'base' ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
                      </button>
                    </div>
                    <p className="instruction-layer-desc">
                      Marco jurídico transversal compartido por todo el despacho (editable en Configuración &gt; Prompt base).
                    </p>
                    <pre className="instruction-code-box">{data.base_prompt}</pre>
                  </div>

                  {/* Capa 2: Tipo de Análisis */}
                  <div className="instruction-layer-card">
                    <div className="instruction-layer-header">
                      <div className="instruction-layer-badge-wrap">
                        <span className="preview-order-badge">2</span>
                        <h4 className="instruction-layer-title">
                          Tipo de Análisis: <strong>{data.type_name}</strong>
                        </h4>
                      </div>
                      <button
                        type="button"
                        className="btn-icon-copy"
                        onClick={() => handleCopy(data.type_instructions, 'type')}
                        title="Copiar instrucciones del tipo"
                        aria-label="Copiar instrucciones del tipo"
                      >
                        {copiedSection === 'type' ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
                      </button>
                    </div>
                    <p className="instruction-layer-desc">
                      Instrucciones especializadas asociadas a este tipo documental específico.
                    </p>
                    <pre className="instruction-code-box">{data.type_instructions}</pre>
                  </div>

                  {/* Capa 3: Nivel de Detalle */}
                  <div className="instruction-layer-card">
                    <div className="instruction-layer-header">
                      <div className="instruction-layer-badge-wrap">
                        <span className="preview-order-badge">3</span>
                        <h4 className="instruction-layer-title">
                          Modificador de Nivel de Detalle:{' '}
                          <span className="inline-badge">{data.detail_level}</span>
                        </h4>
                      </div>
                      <button
                        type="button"
                        className="btn-icon-copy"
                        onClick={() => handleCopy(data.detail_modifier, 'detail')}
                        title="Copiar modificador de detalle"
                        aria-label="Copiar modificador de detalle"
                      >
                        {copiedSection === 'detail' ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
                      </button>
                    </div>
                    <pre className="instruction-code-box instruction-code-sm">{data.detail_modifier}</pre>
                  </div>

                  {/* Capa 4: Formato de Salida */}
                  <div className="instruction-layer-card">
                    <div className="instruction-layer-header">
                      <div className="instruction-layer-badge-wrap">
                        <span className="preview-order-badge">4</span>
                        <h4 className="instruction-layer-title">
                          Modificador de Formato de Salida:{' '}
                          <span className="inline-badge">{data.output_format}</span>
                        </h4>
                      </div>
                      <button
                        type="button"
                        className="btn-icon-copy"
                        onClick={() => handleCopy(data.format_modifier, 'format')}
                        title="Copiar modificador de formato"
                        aria-label="Copiar modificador de formato"
                      >
                        {copiedSection === 'format' ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
                      </button>
                    </div>
                    <pre className="instruction-code-box instruction-code-sm">{data.format_modifier}</pre>
                  </div>

                  {/* Capa 5: Instrucciones Adicionales */}
                  <div className="instruction-layer-card">
                    <div className="instruction-layer-header">
                      <div className="instruction-layer-badge-wrap">
                        <span className="preview-order-badge">5</span>
                        <h4 className="instruction-layer-title">Instrucciones Adicionales del Usuario</h4>
                      </div>
                      {data.additional_instructions && (
                        <button
                          type="button"
                          className="btn-icon-copy"
                          onClick={() => handleCopy(data.additional_instructions || '', 'additional')}
                          title="Copiar instrucciones adicionales"
                          aria-label="Copiar instrucciones adicionales"
                        >
                          {copiedSection === 'additional' ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
                        </button>
                      )}
                    </div>
                    {data.additional_instructions ? (
                      <pre className="instruction-code-box">{data.additional_instructions}</pre>
                    ) : (
                      <p className="instruction-empty-text">
                        (Ninguna instrucción adicional personalizada para esta ejecución)
                      </p>
                    )}
                  </div>
                </div>
              ) : (
                <div className="instructions-integrated-view">
                  <div className="integrated-info-box">
                    <span>
                      Esta es la composición completa de directivas intelectuales que gobernarán el análisis solicitado.
                    </span>
                  </div>
                  <pre className="instruction-code-box instruction-code-large">
                    {data.effective_full_prompt}
                  </pre>
                </div>
              )}
            </>
          ) : null}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn-secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
};
