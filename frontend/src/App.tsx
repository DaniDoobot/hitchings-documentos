import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { InputTabs } from './components/InputTabs';
import { DocumentArea } from './components/DocumentArea';
import { AudioArea } from './components/AudioArea';
import { TextArea } from './components/TextArea';
import { PromptSelector } from './components/PromptSelector';
import { AnalysisOptionsControl } from './components/AnalysisOptionsControl';
import { AnalyzeButton } from './components/AnalyzeButton';
import { AnalysisResult } from './components/AnalysisResult';
import { fetchPrompts } from './api/prompts';
import { extractDocument } from './api/documents';
import { transcribeAudio } from './api/audio';
import { prepareText } from './api/text';
import { analyzeContent } from './api/analysis';
import { getFriendlyErrorMessage } from './utils/errors';
import type {
  InputTab,
  Prompt,
  DetailLevel,
  OutputFormat,
  TranscriptionMode,
  ProcessingStage,
  AnalysisResponse,
  AnalysisRequest,
} from './types/api';
import { Sliders, AlertCircle } from 'lucide-react';

interface CachedDocument {
  file: File;
  text: string;
  warnings: string[];
}

interface CachedAudio {
  file: File;
  mode: TranscriptionMode;
  diarization: boolean;
  text: string;
  warnings: string[];
}

export function App() {
  // Navigation tab
  const [activeTab, setActiveTab] = useState<InputTab>('document');

  // Input states (persisted in React memory across tab changes)
  const [documentFile, setDocumentFile] = useState<File | null>(null);
  const [documentError, setDocumentError] = useState<string | null>(null);

  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [audioMode, setAudioMode] = useState<TranscriptionMode>('verbatim');
  const [audioDiarization, setAudioDiarization] = useState(false);

  const [textContent, setTextContent] = useState('');

  // In-Memory Extraction / Transcription Cache (Strictly React Memory)
  const [cachedDoc, setCachedDoc] = useState<CachedDocument | null>(null);
  const [cachedAudio, setCachedAudio] = useState<CachedAudio | null>(null);

  // Prompts catalog
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selectedPromptId, setSelectedPromptId] = useState('');
  const [isPromptsLoading, setIsPromptsLoading] = useState(true);
  const [promptsError, setPromptsError] = useState<string | null>(null);

  // Analysis options
  const [detailLevel, setDetailLevel] = useState<DetailLevel>('standard');
  const [outputFormat, setOutputFormat] = useState<OutputFormat>('sections');
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // Execution & Processing states
  const [processingStage, setProcessingStage] = useState<ProcessingStage>('idle');
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResponse | null>(null);
  const [processingWarnings, setProcessingWarnings] = useState<string[]>([]);

  // Ref to track current processing stage synchronously for error handling
  const currentStageRef = useRef<ProcessingStage>('idle');
  const updateStage = (stage: ProcessingStage) => {
    currentStageRef.current = stage;
    setProcessingStage(stage);
  };

  const isProcessing =
    processingStage === 'preparing' ||
    processingStage === 'extracting' ||
    processingStage === 'transcribing' ||
    processingStage === 'analyzing';

  // Invalidation of Document Cache when file changes
  const handleDocumentChange = (file: File | null) => {
    setDocumentFile(file);
    setCachedDoc(null);
  };

  // Invalidation of Audio Cache when audio parameters change
  const handleAudioFileChange = (file: File | null) => {
    setAudioFile(file);
    setCachedAudio(null);
  };

  const handleAudioModeChange = (mode: TranscriptionMode) => {
    setAudioMode(mode);
    setCachedAudio(null);
  };

  const handleAudioDiarizationChange = (diarization: boolean) => {
    setAudioDiarization(diarization);
    setCachedAudio(null);
  };

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

  // Stage message for user
  const getProcessingMessage = (): string | null => {
    switch (processingStage) {
      case 'extracting':
        return 'Leyendo documento…';
      case 'transcribing':
        return 'Transcribiendo grabación…';
      case 'preparing':
        return 'Preparando texto…';
      case 'analyzing':
        if (activeTab === 'audio') return 'Analizando transcripción…';
        return 'Analizando contenido…';
      default:
        return null;
    }
  };

  // Main Analysis Workflow Execution
  const handleStartAnalysis = async () => {
    // Protection against concurrent clicks or missing data
    if (isProcessing || !hasContent || !hasPrompt) return;

    setGeneralError(null);

    let preparedText = '';
    let currentProcWarnings: string[] = [];

    try {
      // Step 1: Input preparation / extraction / transcription
      if (activeTab === 'document') {
        if (!documentFile) return;

        // Check in-memory cache
        if (cachedDoc && cachedDoc.file === documentFile) {
          preparedText = cachedDoc.text;
          currentProcWarnings = cachedDoc.warnings;
        } else {
          updateStage('extracting');
          const docRes = await extractDocument(documentFile);
          if (!docRes.text || !docRes.text.trim()) {
            updateStage('error');
            setGeneralError(
              'El documento seleccionado no contiene texto legible para analizar.'
            );
            return;
          }
          preparedText = docRes.text;
          currentProcWarnings = docRes.warnings || [];
          setCachedDoc({
            file: documentFile,
            text: docRes.text,
            warnings: currentProcWarnings,
          });
        }
      } else if (activeTab === 'audio') {
        if (!audioFile) return;

        // Check in-memory cache
        if (
          cachedAudio &&
          cachedAudio.file === audioFile &&
          cachedAudio.mode === audioMode &&
          cachedAudio.diarization === audioDiarization
        ) {
          preparedText = cachedAudio.text;
          currentProcWarnings = cachedAudio.warnings;
        } else {
          updateStage('transcribing');
          const audioRes = await transcribeAudio(
            audioFile,
            audioMode,
            audioDiarization
          );
          if (!audioRes.text || !audioRes.text.trim()) {
            updateStage('error');
            setGeneralError(
              'La grabación de audio no contiene texto inteligible para analizar.'
            );
            return;
          }
          preparedText = audioRes.text;
          currentProcWarnings = audioRes.warnings || [];
          setCachedAudio({
            file: audioFile,
            mode: audioMode,
            diarization: audioDiarization,
            text: audioRes.text,
            warnings: currentProcWarnings,
          });
        }
      } else if (activeTab === 'text') {
        updateStage('preparing');
        const textRes = await prepareText(textContent);
        preparedText = textRes.text;
        currentProcWarnings = [];
      }

      setProcessingWarnings(currentProcWarnings);

      // Step 2: Content Analysis with Gemini via Backend
      updateStage('analyzing');

      const analysisReq: AnalysisRequest = {
        text: preparedText,
        prompt_id: selectedPromptId,
        options: {
          detail_level: detailLevel,
          output_format: outputFormat,
          additional_instructions: additionalInstructions.trim() || undefined,
        },
      };

      const response = await analyzeContent(analysisReq);
      setAnalysisResult(response);
      updateStage('completed');
    } catch (err) {
      const friendlyMessage = getFriendlyErrorMessage(
        err,
        currentStageRef.current,
        activeTab
      );
      updateStage('error');
      setGeneralError(friendlyMessage);
    }
  };

  return (
    <div className="app-container">
      <Header />

      <main className="app-main">
        {generalError && (
          <div className="banner banner-danger" role="alert">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <AlertCircle size={18} />
              <span>{generalError}</span>
            </div>
            <button
              type="button"
              className="btn-secondary-sm"
              onClick={() => setGeneralError(null)}
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
                  onFileSelect={handleDocumentChange}
                  error={documentError}
                  onError={setDocumentError}
                />
              )}

              {activeTab === 'audio' && (
                <AudioArea
                  selectedFile={audioFile}
                  onFileSelect={handleAudioFileChange}
                  error={audioError}
                  onError={setAudioError}
                  mode={audioMode}
                  onModeChange={handleAudioModeChange}
                  diarization={audioDiarization}
                  onDiarizationChange={handleAudioDiarizationChange}
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
                isProcessing={isProcessing}
                processingMessage={getProcessingMessage()}
                onClick={handleStartAnalysis}
              />
            </div>
          </section>
        </div>

        {/* Render Result when available */}
        {analysisResult && (
          <section className="analysis-result-section" aria-label="Resultado del análisis">
            <AnalysisResult
              analysis={analysisResult}
              processingWarnings={processingWarnings}
            />
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
