import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  FileText,
  AlertTriangle,
  Hash,
  Copy,
  Check,
  FileDown,
} from 'lucide-react';
import type { AnalysisResponse, AudioTranscriptionUsage } from '../types/api';
import { exportAnalysisToWord, type WordExportRequest } from '../api/export';
import { ApiError } from '../api/client';

interface AnalysisResultProps {
  analysis: AnalysisResponse;
  processingWarnings?: string[];
  transcriptionUsage?: AudioTranscriptionUsage | null;
}

function formatTokenMetrics(usage?: {
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
} | null): string | null {
  if (!usage) return null;
  const { input_tokens, output_tokens, total_tokens } = usage;
  const hasIn = input_tokens !== null && input_tokens !== undefined;
  const hasOut = output_tokens !== null && output_tokens !== undefined;
  const hasTot = total_tokens !== null && total_tokens !== undefined;

  if (!hasIn && !hasOut && !hasTot) return null;

  if (!hasIn && !hasOut && hasTot) {
    return `${total_tokens!.toLocaleString()} tokens`;
  }

  const parts: string[] = [];
  if (hasIn) {
    parts.push(`${input_tokens!.toLocaleString()} tokens entrada`);
  }
  if (hasOut) {
    parts.push(`${output_tokens!.toLocaleString()} salida`);
  }
  if (hasTot) {
    parts.push(`${total_tokens!.toLocaleString()} total`);
  }
  return parts.join(' · ');
}

export const AnalysisResult: React.FC<AnalysisResultProps> = ({
  analysis,
  processingWarnings = [],
  transcriptionUsage = null,
}) => {
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccessMessage, setExportSuccessMessage] = useState<string | null>(null);
  const [exportErrorMessage, setExportErrorMessage] = useState<string | null>(null);

  const analysisWarnings = analysis.warnings || [];
  const hasWarnings = processingWarnings.length > 0 || analysisWarnings.length > 0;

  const analysisUsageText = formatTokenMetrics(analysis.usage);
  const transcriptionUsageText = formatTokenMetrics(transcriptionUsage);
  const hasAnalysisTokens = analysisUsageText !== null;
  const hasTranscriptionTokens = transcriptionUsageText !== null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(analysis.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback silencioso si no hay acceso al portapapeles
    }
  };

  const handleExportWord = async () => {
    if (isExporting) return;
    setIsExporting(true);
    setExportSuccessMessage(null);
    setExportErrorMessage(null);

    try {
      let combinedWarnings: string[] = [];
      if (processingWarnings.length > 0 && analysisWarnings.length > 0) {
        combinedWarnings = [
          ...processingWarnings.map((w) =>
            w.startsWith('Procesamiento:') ? w : `Procesamiento: ${w}`
          ),
          ...analysisWarnings.map((w) =>
            w.startsWith('Análisis:') ? w : `Análisis: ${w}`
          ),
        ];
      } else if (processingWarnings.length > 0) {
        combinedWarnings = processingWarnings.map((w) =>
          w.startsWith('Procesamiento:') ? w : `Procesamiento: ${w}`
        );
      } else {
        combinedWarnings = [...analysisWarnings];
      }

      const requestPayload: WordExportRequest = {
        title: analysis.title,
        content: analysis.content,
        warnings: combinedWarnings,
        metadata: {
          prompt_name: analysis.prompt_name,
          model: analysis.model,
        },
      };

      const { blob, filename } = await exportAnalysisToWord(requestPayload);

      // Descarga limpia en el cliente sin persistencia
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = filename || 'hitchings-analisis.docx';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setExportSuccessMessage('Word generado correctamente');
      setTimeout(() => setExportSuccessMessage(null), 3000);
    } catch (err) {
      if (err instanceof ApiError && err.status === 413) {
        setExportErrorMessage(
          'El resultado es demasiado extenso para exportarlo a Word.'
        );
      } else {
        setExportErrorMessage(
          'No se ha podido generar el archivo Word. Inténtalo de nuevo.'
        );
      }
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="card analysis-result-card" data-testid="analysis-result">
      {/* Header */}
      <div className="card-header result-card-header">
        <div className="result-header-top">
          <div className="result-badge-row">
            <span className="result-prompt-badge">
              <FileText size={14} />
              {analysis.prompt_name}
            </span>
          </div>

          <div className="result-actions-row">
            <button
              type="button"
              className="btn-action-sm"
              onClick={handleCopy}
              title="Copiar contenido en Markdown"
            >
              {copied ? <Check size={14} color="#16a34a" /> : <Copy size={14} />}
              <span>{copied ? '¡Copiado!' : 'Copiar'}</span>
            </button>

            <button
              type="button"
              className="btn-action-sm btn-action-primary"
              onClick={handleExportWord}
              disabled={isExporting}
              title="Exportar análisis a documento Microsoft Word (.docx)"
            >
              {isExporting ? (
                <span className="spinner-sm" aria-hidden="true" />
              ) : (
                <FileDown size={14} />
              )}
              <span>{isExporting ? 'Generando Word…' : 'Exportar a Word'}</span>
            </button>
          </div>
        </div>

        <h2 className="result-title">{analysis.title}</h2>

        {exportSuccessMessage && (
          <div className="export-status-banner success" role="status">
            <Check size={14} />
            <span>{exportSuccessMessage}</span>
          </div>
        )}

        {exportErrorMessage && (
          <div className="export-status-banner error" role="alert">
            <AlertTriangle size={14} />
            <span>{exportErrorMessage}</span>
          </div>
        )}
      </div>

      {/* Body: Rendered Markdown */}
      <div className="card-body result-body">
        <article className="markdown-document" data-testid="markdown-content">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {analysis.content}
          </ReactMarkdown>
        </article>

        {/* Combined Warnings Section */}
        {hasWarnings && (
          <section className="result-warnings-box" aria-label="Advertencias">
            <div className="result-warnings-header">
              <AlertTriangle size={18} color="#d97706" />
              <h3 className="result-warnings-title">Advertencias</h3>
            </div>

            {processingWarnings.length > 0 && (
              <div className="warnings-group">
                <p className="warnings-group-title">
                  Procesamiento y Extracción:
                </p>
                <ul className="warnings-list">
                  {processingWarnings.map((w, idx) => (
                    <li key={`proc-${idx}`}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            {analysisWarnings.length > 0 && (
              <div className="warnings-group">
                <p className="warnings-group-title">Análisis Documental:</p>
                <ul className="warnings-list">
                  {analysisWarnings.map((w, idx) => (
                    <li key={`ana-${idx}`}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </section>
        )}

        {/* Discrete Technical Metrics Footer */}
        {(hasAnalysisTokens || hasTranscriptionTokens) && (
          <footer
            className={`result-metrics-footer ${hasTranscriptionTokens ? 'multi-stage' : ''}`}
            aria-label="Consumo de tokens"
          >
            {hasTranscriptionTokens ? (
              <div className="metrics-multi-stage-container">
                <div className="metrics-header-row">
                  <Hash size={13} />
                  <span className="metrics-main-title">Uso de IA</span>
                </div>
                <div className="metrics-stages-list">
                  {transcriptionUsageText && (
                    <div className="metrics-stage-item">
                      <span className="stage-label">Transcripción:</span>
                      <span className="stage-value">{transcriptionUsageText}</span>
                    </div>
                  )}
                  {analysisUsageText && (
                    <div className="metrics-stage-item">
                      <span className="stage-label">Análisis:</span>
                      <span className="stage-value">{analysisUsageText}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="metrics-group">
                <Hash size={13} />
                <span className="stage-label">Análisis:</span>
                <span className="stage-value">{analysisUsageText}</span>
              </div>
            )}
          </footer>
        )}
      </div>
    </div>
  );
};
