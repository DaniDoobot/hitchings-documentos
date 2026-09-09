import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import type { Prompt } from '../types/api';

interface PromptSelectorProps {
  prompts: Prompt[];
  selectedPromptId: string;
  onSelectPrompt: (promptId: string) => void;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

export const PromptSelector: React.FC<PromptSelectorProps> = ({
  prompts,
  selectedPromptId,
  onSelectPrompt,
  isLoading,
  error,
  onRetry,
}) => {
  const selectedPrompt = prompts.find((p) => p.id === selectedPromptId);

  return (
    <div className="form-field">
      <label htmlFor="prompt-select" className="field-label">
        Tipo de análisis (Prompt)
      </label>

      {isLoading ? (
        <div
          style={{
            padding: '0.75rem',
            background: '#f1f5f9',
            borderRadius: '8px',
            fontSize: '0.85rem',
            color: '#64748b',
          }}
        >
          Cargando catálogo de análisis...
        </div>
      ) : error ? (
        <div className="banner banner-danger" role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="banner-retry-btn"
            onClick={onRetry}
            style={{ display: 'flex', alignItems: 'center', gap: '4px' }}
          >
            <RefreshCw size={12} />
            Reintentar
          </button>
        </div>
      ) : (
        <>
          <select
            id="prompt-select"
            className="custom-select"
            value={selectedPromptId}
            onChange={(e) => onSelectPrompt(e.target.value)}
            disabled={prompts.length === 0}
          >
            <option value="" disabled>
              -- Selecciona un tipo de análisis --
            </option>
            {prompts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>

          {selectedPrompt && (
            <div className="prompt-preview-box">
              <p style={{ fontWeight: 600, color: '#0f2b48', marginBottom: '0.25rem' }}>
                {selectedPrompt.name}
              </p>
              <p>{selectedPrompt.description}</p>
            </div>
          )}
        </>
      )}
    </div>
  );
};
