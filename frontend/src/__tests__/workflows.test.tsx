import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as promptsApi from '../api/prompts';
import * as docsApi from '../api/documents';
import * as audioApi from '../api/audio';
import * as textApi from '../api/text';
import * as analysisApi from '../api/analysis';
import { ApiError } from '../api/client';
import type {
  Prompt,
  DocumentExtractResponse,
  AudioTranscribeResponse,
  TextPrepareResponse,
  AnalysisResponse,
} from '../types/api';

const mockPrompts: Prompt[] = [
  {
    id: 'legal-analysis',
    name: 'Análisis Jurídico Integral',
    description: 'Dictamen exhaustivo de riesgos legales.',
    instructions: 'Analiza el documento...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
  {
    id: 'executive-summary',
    name: 'Resumen Ejecutivo',
    description: 'Síntesis concisa de los puntos clave.',
    instructions: 'Genera un resumen ejecutivo...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
];

const mockDocResponse: DocumentExtractResponse = {
  filename: 'contrato.pdf',
  extension: 'pdf',
  content_type: 'application/pdf',
  size_bytes: 1024,
  page_count: 2,
  word_count: 50,
  character_count: 300,
  text: 'Contrato de servicios entre Parte A y Parte B.',
  warnings: ['Página 2 contiene texto manuscrito o escaneado'],
};

const mockAudioResponse: AudioTranscribeResponse = {
  filename: 'grabacion.mp3',
  extension: 'mp3',
  content_type: 'audio/mpeg',
  size_bytes: 2048,
  transcription_model: 'gemini-3.5-transcribe',
  mode: 'verbatim',
  diarization: false,
  text: 'Transcripción de la reunión sobre el contrato.',
  word_count: 7,
  character_count: 45,
  segments: [],
  warnings: ['Se detectó ruido de fondo en el minuto 01:15'],
};

const mockTextResponse: TextPrepareResponse = {
  text: 'Texto preparado y normalizado para análisis.',
  word_count: 6,
  character_count: 44,
};

const mockAnalysisResponse: AnalysisResponse = {
  prompt_id: 'legal-analysis',
  prompt_name: 'Análisis Jurídico Integral',
  model: 'gemini-3.8-flash',
  options: { detail_level: 'standard', output_format: 'sections' },
  title: 'Dictamen Jurídico sobre Contrato',
  content: `## 1. Naturaleza Jurídica\nContrato civil de arrendamiento.\n\n## 2. Obligaciones\n- Entrega de **fianza** de 500 euros.\n- Mantenimiento ordinario.`,
  warnings: ['No se especifica cláusula de fuero judicial'],
  usage: { input_tokens: 1540, output_tokens: 320, total_tokens: 1860 },
};

describe('HITCHINGS Documentos - Flujos Extremo a Extremo (Bloque 6B)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue(mockPrompts);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderAndAwaitReady = async () => {
    render(<App />);
    await waitFor(() => {
      expect(
        screen.queryByText(/Cargando catálogo de análisis.../i)
      ).not.toBeInTheDocument();
      expect(
        screen.getByDisplayValue(/Análisis Jurídico Integral/i)
      ).toBeInTheDocument();
    });
  };

  it('1. Documento válido llama a extractDocument (/documents/extract)', async () => {
    const extractSpy = vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    const btn = screen.getByRole('button', { name: /analizar documento/i });
    fireEvent.click(btn);

    await waitFor(() => {
      expect(extractSpy).toHaveBeenCalledTimes(1);
      expect(extractSpy).toHaveBeenCalledWith(file);
    });
  });

  it('2. El texto extraído del documento se envía a analyzeContent (/analysis)', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    const analysisSpy = vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(analysisSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          text: mockDocResponse.text,
          prompt_id: 'legal-analysis',
        })
      );
    });
  });

  it('3. Pipeline completo de documento: extracción -> análisis -> visualización', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(screen.getByText('Dictamen Jurídico sobre Contrato')).toBeInTheDocument();
      expect(screen.getByText(/Naturaleza Jurídica/i)).toBeInTheDocument();
    });
  });

  it('4. Documento sin texto legible detiene el flujo y no llama a /analysis', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue({
      ...mockDocResponse,
      text: '   ',
    });
    const analysisSpy = vi.spyOn(analysisApi, 'analyzeContent');

    await renderAndAwaitReady();

    const file = new File(['empty content'], 'vacio.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/no contiene texto legible para analizar/i)
      ).toBeInTheDocument();
    });
    expect(analysisSpy).not.toHaveBeenCalled();
  });

  it('5. Los warnings de extracción del documento se preservan y muestran en el resultado', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(
        screen.getByText('Página 2 contiene texto manuscrito o escaneado')
      ).toBeInTheDocument();
    });
  });

  it('6. Audio válido llama a transcribeAudio (/audio/transcribe)', async () => {
    const audioSpy = vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio content'], 'grabacion.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);

    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(audioSpy).toHaveBeenCalledWith(audioFile, 'verbatim', false);
    });
  });

  it('7. La transcripción de audio se envía a analyzeContent (/analysis)', async () => {
    vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    const analysisSpy = vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio content'], 'grabacion.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);

    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(analysisSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          text: mockAudioResponse.text,
        })
      );
    });
  });

  it('8. Pipeline completo de audio: transcripción -> análisis -> visualización', async () => {
    vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio content'], 'grabacion.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);

    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(screen.getByText('Dictamen Jurídico sobre Contrato')).toBeInTheDocument();
    });
  });

  it('9. Texto pegado llama a prepareText (/text/prepare)', async () => {
    const textSpy = vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/Pega o escribe aquí el contenido/i);
    fireEvent.change(textarea, { target: { value: 'Texto de contrato para analizar.' } });

    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(textSpy).toHaveBeenCalledWith('Texto de contrato para analizar.');
    });
  });

  it('10. Texto normalizado se envía a analyzeContent (/analysis)', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    const analysisSpy = vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/Pega o escribe aquí el contenido/i);
    fireEvent.change(textarea, { target: { value: 'Texto de contrato.' } });

    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(analysisSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          text: mockTextResponse.text,
        })
      );
    });
  });

  it('11. Renderiza correctamente Markdown estructurado en el resultado', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      const heading = screen.getByRole('heading', { name: /1\. Naturaleza Jurídica/i });
      expect(heading).toBeInTheDocument();
      expect(screen.getByText(/fianza/i).tagName).toBe('STRONG');
    });
  });

  it('12. Muestra los warnings devueltos por el análisis', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Contrato' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(
        screen.getByText('No se especifica cláusula de fuero judicial')
      ).toBeInTheDocument();
    });
  });

  it('13. Diferencia visualmente warnings de procesamiento y de análisis', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(screen.getByText(/Procesamiento y Extracción:/i)).toBeInTheDocument();
      expect(screen.getByText(/Análisis Documental:/i)).toBeInTheDocument();
    });
  });

  it('14. Muestra discretamente las métricas de tokens en el footer del resultado', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Texto' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText('Dictamen Jurídico sobre Contrato')).toBeInTheDocument();
    });

    const footer = document.querySelector('.result-metrics-footer');
    expect(footer).toBeInTheDocument();
    expect(footer).toHaveTextContent(/tokens entrada/i);
    expect(footer).toHaveTextContent(/1540|1\.540|1,540/);
    expect(footer).toHaveTextContent(/salida/i);
    expect(footer).toHaveTextContent(/320/);
    expect(footer).toHaveTextContent(/total/i);
    expect(footer).toHaveTextContent(/1860|1\.860|1,860/);
  });

  it('15. Captura error durante la extracción y muestra mensaje contextual', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockRejectedValue(new ApiError('Error al leer PDF', 500));

    await renderAndAwaitReady();

    const file = new File(['pdf content'], 'contrato.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/No se ha podido extraer el contenido del documento/i)
      ).toBeInTheDocument();
    });
  });

  it('16. Captura error durante la transcripción y muestra mensaje contextual', async () => {
    vi.spyOn(audioApi, 'transcribeAudio').mockRejectedValue(new ApiError('Audio corrupto', 400));

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio'], 'audio.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(screen.getByText('Audio corrupto')).toBeInTheDocument();
    });
  });

  it('17. Captura error durante el análisis y muestra mensaje contextual de audio', async () => {
    vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockRejectedValue(new ApiError('Fallo de Gemini', 500));

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio'], 'audio.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/La transcripción se completó, pero no se pudo realizar el análisis/i)
      ).toBeInTheDocument();
    });
  });

  it('18. Error 413 contextual según la etapa activa', async () => {
    vi.spyOn(docsApi, 'extractDocument').mockRejectedValue(new ApiError('Payload too large', 413));

    await renderAndAwaitReady();

    const file = new File(['big pdf'], 'big.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(
        screen.getByText('El documento supera el tamaño permitido.')
      ).toBeInTheDocument();
    });
  });

  it('19. Error 503 contextual para indisponibilidad del servicio', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockRejectedValue(new ApiError('Service unavailable', 503));

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Contrato texto' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(
        screen.getByText(/El servicio de análisis no está disponible temporalmente/i)
      ).toBeInTheDocument();
    });
  });

  it('20. El botón de análisis se bloquea y muestra estado de procesamiento', async () => {
    let resolveExtract: (val: DocumentExtractResponse) => void;
    const pendingExtract = new Promise<DocumentExtractResponse>((res) => {
      resolveExtract = res;
    });
    vi.spyOn(docsApi, 'extractDocument').mockReturnValue(pendingExtract);

    await renderAndAwaitReady();

    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    const btn = screen.getByRole('button', { name: /analizar documento/i });
    fireEvent.click(btn);

    expect(btn).toBeDisabled();
    expect(screen.getByText(/Leyendo documento…/i)).toBeInTheDocument();

    resolveExtract!(mockDocResponse);
  });

  it('21. Doble submit mientras procesa es ignorado y no duplica llamadas', async () => {
    let resolveText: (val: TextPrepareResponse) => void;
    const pendingText = new Promise<TextPrepareResponse>((res) => {
      resolveText = res;
    });
    const prepareSpy = vi.spyOn(textApi, 'prepareText').mockReturnValue(pendingText);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Texto' } });

    const btn = screen.getByRole('button', { name: /analizar texto/i });
    fireEvent.click(btn);
    fireEvent.click(btn); // Segundo click inmediato

    expect(prepareSpy).toHaveBeenCalledTimes(1);
    resolveText!(mockTextResponse);
  });

  it('22. Tras completar un análisis, cambiar de prompt permite reanalizar', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    const analysisSpy = vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Texto' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText('Dictamen Jurídico sobre Contrato')).toBeInTheDocument();
    });

    // Cambiar de prompt
    const select = screen.getByLabelText(/Tipo de análisis \(Prompt\)/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });

    // Botón sigue habilitado para reanalizar
    const btn = screen.getByRole('button', { name: /analizar texto/i });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);

    await waitFor(() => {
      expect(analysisSpy).toHaveBeenCalledTimes(2);
      expect(analysisSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({ prompt_id: 'executive-summary' })
      );
    });
  });

  it('23. Documento cacheado no se vuelve a extraer si solo cambia el prompt', async () => {
    const extractSpy = vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(extractSpy).toHaveBeenCalledTimes(1);
    });

    // Cambiar de prompt
    const select = screen.getByLabelText(/Tipo de análisis \(Prompt\)/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });

    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      // No debe haberse vuelto a extraer
      expect(extractSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('24. Audio cacheado no se vuelve a transcribir si solo cambia el prompt', async () => {
    const transcribeSpy = vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio'], 'audio.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(1);
    });

    // Cambiar prompt
    const select = screen.getByLabelText(/Tipo de análisis \(Prompt\)/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });

    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('25. Cambio de archivo de audio invalida el cache y vuelve a transcribir', async () => {
    const transcribeSpy = vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile1 = new File(['audio1'], 'audio1.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile1);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(1);
    });

    // Subir otro archivo de audio
    const audioFile2 = new File(['audio2'], 'audio2.mp3', { type: 'audio/mpeg' });
    fireEvent.click(screen.getByLabelText(/Eliminar audio/i));
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile2);

    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(2);
    });
  });

  it('26. Cambio de modo de audio invalida el cache de audio', async () => {
    const transcribeSpy = vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio'], 'audio.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(1);
    });

    // Cambiar a Normalizado (smart)
    fireEvent.click(screen.getByLabelText(/Normalizado \(Smart\)/i));
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(2);
    });
  });

  it('27. Cambio de diarización en audio invalida el cache de audio', async () => {
    const transcribeSpy = vi.spyOn(audioApi, 'transcribeAudio').mockResolvedValue(mockAudioResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    const audioFile = new File(['audio'], 'audio.mp3', { type: 'audio/mpeg' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de audio/i), audioFile);
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(1);
    });

    // Activar diarización
    fireEvent.click(screen.getByLabelText(/Activar diarización/i));
    fireEvent.click(screen.getByRole('button', { name: /transcribir y analizar/i }));

    await waitFor(() => {
      expect(transcribeSpy).toHaveBeenCalledTimes(2);
    });
  });

  it('28. No se utiliza localStorage ni sessionStorage para persistir datos', async () => {
    const localSpy = vi.spyOn(Storage.prototype, 'setItem');

    vi.spyOn(docsApi, 'extractDocument').mockResolvedValue(mockDocResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysisResponse);

    await renderAndAwaitReady();

    const file = new File(['pdf'], 'doc.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);
    fireEvent.click(screen.getByRole('button', { name: /analizar documento/i }));

    await waitFor(() => {
      expect(screen.getByText('Dictamen Jurídico sobre Contrato')).toBeInTheDocument();
    });

    expect(localSpy).not.toHaveBeenCalled();
  });

  it('29. El catálogo de prompts sigue cargado y utilizable tras un error de análisis', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue(mockTextResponse);
    vi.spyOn(analysisApi, 'analyzeContent').mockRejectedValue(new ApiError('Error 500', 500));

    await renderAndAwaitReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/Pega o escribe aquí/i), { target: { value: 'Texto' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    // El selector de prompts sigue presente con sus opciones
    const select = screen.getByLabelText(/Tipo de análisis \(Prompt\)/i);
    expect(select).toBeInTheDocument();
    expect(screen.getByText('Resumen Ejecutivo')).toBeInTheDocument();
  });
});
