import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText, AlertTriangle, Cpu, Hash } from 'lucide-react';
import type { AnalysisResponse } from '../types/api';

interface AnalysisResultProps {
  analysis: AnalysisResponse;
  processingWarnings?: string[];
}

export const AnalysisResult: React.FC<AnalysisResultProps> = ({
  analysis,
  processingWarnings = [],
}) => {
  const analysisWarnings = analysis.warnings || [];
  const hasWarnings = processingWarnings.length > 0 || analysisWarnings.length > 0;

  const usage = analysis.usage;
  const hasTokens =
    usage &&
    (usage.input_tokens !== null ||
      usage.output_tokens !== null ||
      usage.total_tokens !== null);

  return (
    <div className="card analysis-result-card" data-testid="analysis-result">
      {/* Header */}
      <div className="card-header result-card-header">
        <div className="result-badge-row">
          <span className="result-prompt-badge">
            <FileText size={14} />
            {analysis.prompt_name}
          </span>
          <span className="result-model-badge">
            <Cpu size={14} />
            {analysis.model}
          </span>
        </div>
        <h2 className="result-title">{analysis.title}</h2>
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
        {hasTokens && (
          <footer className="result-metrics-footer">
            <div className="metrics-group">
              <Hash size={13} />
              {usage.input_tokens !== null && (
                <span>
                  <strong>{usage.input_tokens.toLocaleString()}</strong> tokens entrada
                </span>
              )}
              {usage.output_tokens !== null && (
                <>
                  <span className="metric-separator">·</span>
                  <span>
                    <strong>{usage.output_tokens.toLocaleString()}</strong> salida
                  </span>
                </>
              )}
              {usage.total_tokens !== null && (
                <>
                  <span className="metric-separator">·</span>
                  <span>
                    <strong>{usage.total_tokens.toLocaleString()}</strong> total
                  </span>
                </>
              )}
            </div>
          </footer>
        )}
      </div>
    </div>
  );
};
