import React from 'react';
import type { DetailLevel, OutputFormat } from '../types/api';

const MAX_INSTRUCTIONS_LENGTH = 10000;

interface AnalysisOptionsControlProps {
  detailLevel: DetailLevel;
  onDetailLevelChange: (level: DetailLevel) => void;
  outputFormat: OutputFormat;
  onOutputFormatChange: (format: OutputFormat) => void;
  additionalInstructions: string;
  onAdditionalInstructionsChange: (instructions: string) => void;
}

export const AnalysisOptionsControl: React.FC<AnalysisOptionsControlProps> = ({
  detailLevel,
  onDetailLevelChange,
  outputFormat,
  onOutputFormatChange,
  additionalInstructions,
  onAdditionalInstructionsChange,
}) => {
  return (
    <div className="analysis-options-control">
      <div className="form-field">
        <label className="field-label">Nivel de profundidad</label>
        <div className="segmented-control" role="group" aria-label="Nivel de detalle">
          <button
            type="button"
            className={`segmented-option ${detailLevel === 'brief' ? 'active' : ''}`}
            onClick={() => onDetailLevelChange('brief')}
          >
            Resumido
          </button>
          <button
            type="button"
            className={`segmented-option ${detailLevel === 'standard' ? 'active' : ''}`}
            onClick={() => onDetailLevelChange('standard')}
          >
            Estándar
          </button>
          <button
            type="button"
            className={`segmented-option ${detailLevel === 'detailed' ? 'active' : ''}`}
            onClick={() => onDetailLevelChange('detailed')}
          >
            Detallado
          </button>
        </div>
      </div>

      <div className="form-field">
        <label className="field-label">Estructura de salida</label>
        <div className="segmented-control" role="group" aria-label="Estructura del análisis">
          <button
            type="button"
            className={`segmented-option ${outputFormat === 'prose' ? 'active' : ''}`}
            onClick={() => onOutputFormatChange('prose')}
          >
            Prosa continua
          </button>
          <button
            type="button"
            className={`segmented-option ${outputFormat === 'sections' ? 'active' : ''}`}
            onClick={() => onOutputFormatChange('sections')}
          >
            Secciones temáticas
          </button>
          <button
            type="button"
            className={`segmented-option ${outputFormat === 'bullet_points' ? 'active' : ''}`}
            onClick={() => onOutputFormatChange('bullet_points')}
          >
            Puntos clave
          </button>
        </div>
      </div>

      <div className="form-field">
        <label htmlFor="additional-instructions" className="field-label">
          Instrucciones adicionales (opcional)
        </label>
        <textarea
          id="additional-instructions"
          className="custom-textarea"
          style={{ minHeight: '85px', fontSize: '0.82rem' }}
          placeholder="Ejemplo: Prestar especial atención a la cláusula quinta sobre indemnizaciones..."
          value={additionalInstructions}
          onChange={(e) => {
            if (e.target.value.length <= MAX_INSTRUCTIONS_LENGTH) {
              onAdditionalInstructionsChange(e.target.value);
            }
          }}
          maxLength={MAX_INSTRUCTIONS_LENGTH}
        />
        <div
          style={{
            display: 'flex',
            justifyContent: 'flex-end',
            fontSize: '0.75rem',
            color: '#94a3b8',
            marginTop: '0.2rem',
          }}
        >
          <span>
            {additionalInstructions.length.toLocaleString()} / {MAX_INSTRUCTIONS_LENGTH.toLocaleString()} caracteres
          </span>
        </div>
      </div>
    </div>
  );
};
