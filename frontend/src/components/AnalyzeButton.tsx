import React from 'react';
import { Play } from 'lucide-react';
import type { InputTab } from '../types/api';

interface AnalyzeButtonProps {
  tab: InputTab;
  hasContent: boolean;
  hasPrompt: boolean;
  onClick: () => void;
}

export const AnalyzeButton: React.FC<AnalyzeButtonProps> = ({
  tab,
  hasContent,
  hasPrompt,
  onClick,
}) => {
  const getButtonLabel = (): string => {
    switch (tab) {
      case 'document':
        return 'Analizar documento';
      case 'audio':
        return 'Transcribir y analizar';
      case 'text':
        return 'Analizar texto';
      default:
        return 'Iniciar análisis';
    }
  };

  const isEnabled = hasContent && hasPrompt;

  const getStatusText = (): string => {
    if (!hasContent && !hasPrompt) {
      return 'Selecciona un contenido y un tipo de análisis para comenzar';
    }
    if (!hasContent) {
      return tab === 'audio'
        ? 'Carga un archivo de audio para habilitar la transcripción'
        : 'Carga un documento o introduce texto para habilitar el análisis';
    }
    if (!hasPrompt) {
      return 'Selecciona un tipo de análisis para continuar';
    }
    return 'Configuración lista para procesar';
  };

  return (
    <div>
      <button
        type="button"
        className="btn-primary-cta"
        disabled={!isEnabled}
        onClick={onClick}
        aria-label={getButtonLabel()}
      >
        <Play size={18} fill={isEnabled ? '#ffffff' : '#94a3b8'} />
        <span>{getButtonLabel()}</span>
      </button>
      <p className="cta-status-help">{getStatusText()}</p>
    </div>
  );
};
