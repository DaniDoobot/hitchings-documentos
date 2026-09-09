import { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { InputTabs } from './components/InputTabs';
import { DocumentArea } from './components/DocumentArea';
import { AudioArea } from './components/AudioArea';
import { TextArea } from './components/TextArea';
import { PromptSelector } from './components/PromptSelector';
import { AnalysisOptionsControl } from './components/AnalysisOptionsControl';
import { AnalyzeButton } from './components/AnalyzeButton';
import { fetchPrompts } from './api/prompts';
import type {
  InputTab,
  Prompt,
  DetailLevel,
  OutputFormat,
  TranscriptionMode,
} from './types/api';
import { Sliders } from 'lucide-react';

export function App() {
  // Navigation tab
  const [activeTab, setActiveTab] = useState<InputTab>('document');

  // Input states (persisted across tab changes)
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);

  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [audioMode, setAudioMode] = useState<TranscriptionMode>('verbatim');
  const [audioDiarization, setAudioDiarization] = useState(false);

  const [textContent, setTextContent] = useState('');

  // Prompts catalog
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [isPromptsLoading, setIsPromptsLoading] = useState(true);
  const [promptsError, setPromptsError] = useState<string | null>(null);

  // Analysis options
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('standard');
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('sections');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // UI feedback message
  const [notification, setNotification] = useState<string | null>(null);

  const loadPromptsCatalog = useCallback(async () => {
    setIsPromptsLoading(true);
    setPromptsError(null);
    try {
      const data = await fetchPrompts();
      setPrompts(data);
      setSelectedPromptId((prev) => (prev ? prev : (data[0]?.id || '')));
    } catch (err) {
      setPromptsError(
        err instanceof Error
          ? err.message
          : 'No se pudo cargar el catálogo de análisis'
      );
    } finally {
      setIsPromptsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPromptsCatalog();
  }, [loadPromptsCatalog]);

  // Determine if active avenue has content
  const hasContent = (() => {
    switch (activeTab) {
      case 'document':
        return documentFile !== null;
      case 'audio':
        return audioFile !== null;
      case 'text':
        return textContent.trim().length > 0;
      default:
        return false;
    }
  })();

  const hasPrompt = Boolean(selectedPromptId);

  const handleStartAnalysis = () => {
    if (!hasContent || !hasPrompt) return;
    setNotification(
      'Configuración validada. La ejecución del análisis se conectará en el Bloque 6B.'
    );
  };

  return (
    <div className="app-container">
      <Header />

      <main className="app-main">
        {notification && (
          <div
            className="banner"
            style={{
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              color: '#1e40af',
            }}
            role="status"
          >
            <span>{notification}</span>
            <button
              type="button"
              className="btn-secondary-sm"
              onClick={() => setNotification(null)}
            >
              Cerrar
            </button>
          </div>
        )}

        <div className="workspace-grid">
          {/* Left panel: Input avenues */}
          <section className="card" aria-label="Entrada de contenido">
            <InputTabs activeTab={activeTab} onSelectTab={setActiveTab} />

            <div className="card-body">
              {activeTab === 'document' && (
                <DocumentArea
                  selectedFile={documentFile}
                  onFileSelect={setDocumentFile}
                  error={documentError}
                  onError={setDocumentError}
                />
              )}

              {activeTab === 'audio' && (
                <AudioArea
                  selectedFile={audioFile}
                  onFileSelect={setAudioFile}
                  error={audioError}
                  onError={setAudioError}
                  mode={audioMode}
                  onModeChange={setAudioMode}
                  diarization={audioDiarization}
                  onDiarizationChange={setAudioDiarization}
                />
              )}

              {activeTab === 'text' && (
                <TextArea
                  text={textContent}
                  onTextChange={setTextContent}
                />
              )}
            </div>
          </section>

          {/* Right panel: Analysis parameters */}
          <section className="card" aria-label="Opciones de análisis">
            <div className="card-header">
              <h2 className="card-title">
                <Sliders size={18} color="#2563eb" />
                Configuración del Análisis
              </h2>
              <p className="card-description">
                Selecciona la plantilla de análisis y personaliza los parámetros de salida.
              </p>
            </div>

            <div className="card-body">
              <PromptSelector
                prompts={prompts}
                selectedPromptId={selectedPromptId}
                onSelectPrompt={setSelectedPromptId}
                isLoading={isPromptsLoading}
                error={promptsError}
                onRetry={loadPromptsCatalog}
              />

              <AnalysisOptionsControl
                detailLevel={detailLevel}
                onDetailLevelChange={setDetailLevel}
                outputFormat={outputFormat}
                onOutputFormatChange={setOutputFormat}
                additionalInstructions={additionalInstructions}
                onAdditionalInstructionsChange={setAdditionalInstructions}
              />

              <AnalyzeButton
                tab={activeTab}
                hasContent={hasContent}
                hasPrompt={hasPrompt}
                onClick={handleStartAnalysis}
              />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
