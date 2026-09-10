import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AnalysisResult } from '../components/AnalysisResult';
import { App } from '../App';
import * as exportApi from '../api/export';
import * as promptsApi from '../api/prompts';
import * as textApi from '../api/text';
import * as analysisApi from '../api/analysis';
import { ApiError } from '../api/client';
import type { AnalysisResponse, Prompt } from '../types/api';

const mockAnalysis: AnalysisResponse = {
  prompt_id: 'legal-analysis',
  prompt_name: 'Análisis Jurídico Integral',
  model: 'gemini-3.8-flash',
  options: { detail_level: 'standard', output_format: 'sections' },
  title: 'Dictamen Jurídico sobre Contrato',
  content: '## 1. Cláusulas Clave\nContenido del dictamen legal.\n\n## 2. Obligaciones\n- Obligación A.',
  warnings: ['No se incluye cláusula penal'],
  usage: { input_tokens: 500, output_tokens: 150, total_tokens: 650 },
};

const mockPrompts: Prompt[] = [
  {
    id: 'legal-analysis',
    name: 'Análisis Jurídico Integral',
    description: 'Dictamen exhaustivo.',
    instructions: 'Analiza el documento...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
  {
    id: 'executive-summary',
    name: 'Resumen Ejecutivo',
    description: 'Síntesis ejecutiva.',
    instructions: 'Genera un resumen...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
];

describe('HITCHINGS Documentos - Exportación Word y UX (Bloque 6C)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue(mockPrompts);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('1. El botón Exportar a Word aparece cuando existe un resultado de análisis', () => {
    render(<AnalysisResult analysis={mockAnalysis} />);
    expect(screen.getByRole('button', { name: /exportar a word/i })).toBeInTheDocument();
  });

  it('2. El botón Exportar a Word no aparece en la interfaz inicial sin análisis', async () => {
    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/cargando catálogo/i)).not.toBeInTheDocument();
    });
    expect(screen.queryByRole('button', { name: /exportar a word/i })).not.toBeInTheDocument();
  });

  it('3 y 4. Envía payload correcto a exportAnalysisToWord sin tokens ni datos privados', async () => {
    const exportSpy = vi.spyOn(exportApi, 'exportAnalysisToWord').mockResolvedValue({
      blob: new Blob(['fake docx'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }),
      filename: 'analisis-juridico.docx',
    });

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(exportSpy).toHaveBeenCalledTimes(1);
      expect(exportSpy).toHaveBeenCalledWith({
        title: mockAnalysis.title,
        content: mockAnalysis.content,
        warnings: mockAnalysis.warnings,
        metadata: {
          prompt_name: mockAnalysis.prompt_name,
          model: mockAnalysis.model,
        },
      });
    });

    // Validar que no se transmitieron los tokens en el payload
    const calledPayload = exportSpy.mock.calls[0][0] as any;
    expect(calledPayload.usage).toBeUndefined();
    expect(calledPayload.input_tokens).toBeUndefined();
  });

  it('5. Incluye warnings de procesamiento y análisis diferenciados en el payload', async () => {
    const exportSpy = vi.spyOn(exportApi, 'exportAnalysisToWord').mockResolvedValue({
      blob: new Blob(['fake docx']),
      filename: 'analisis.docx',
    });

    render(
      <AnalysisResult
        analysis={mockAnalysis}
        processingWarnings={['Página 3 contiene texto manuscrito']}
      />
    );
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(exportSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          warnings: [
            'Procesamiento: Página 3 contiene texto manuscrito',
            'Análisis: No se incluye cláusula penal',
          ],
        })
      );
    });
  });

  it('6, 7, 8, 9 y 10. Descarga Blob, usa filename, invoca URL.createObjectURL y revokeObjectURL', async () => {
    const mockBlob = new Blob(['docx content'], { type: 'application/docx' });
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockResolvedValue({
      blob: mockBlob,
      filename: 'contrato_final_2026.docx',
    });

    const createObjectURLMock = vi.fn().mockReturnValue('blob:http://localhost:5173/mock-uuid');
    const revokeObjectURLMock = vi.fn();
    window.URL.createObjectURL = createObjectURLMock;
    window.URL.revokeObjectURL = revokeObjectURLMock;

    let capturedDownload: string | null = null;
    const origCreateElement = document.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName.toLowerCase() === 'a') {
        const origClick = el.click.bind(el);
        el.click = () => {
          capturedDownload = el.getAttribute('download') || (el as HTMLAnchorElement).download;
          origClick();
        };
      }
      return el;
    });

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(createObjectURLMock).toHaveBeenCalledWith(mockBlob);
      expect(revokeObjectURLMock).toHaveBeenCalledWith('blob:http://localhost:5173/mock-uuid');
      expect(capturedDownload).toBe('contrato_final_2026.docx');
    });

    createElementSpy.mockRestore();
  });

  it('usa fallback hitchings-analisis.docx si exportAnalysisToWord devuelve filename vacío', async () => {
    const mockBlob = new Blob(['docx content'], { type: 'application/docx' });
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockResolvedValue({
      blob: mockBlob,
      filename: '',
    });

    let capturedDownload: string | null = null;
    const origCreateElement = document.createElement.bind(document);
    const createElementSpy = vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const el = origCreateElement(tagName);
      if (tagName.toLowerCase() === 'a') {
        const origClick = el.click.bind(el);
        el.click = () => {
          capturedDownload = el.getAttribute('download') || (el as HTMLAnchorElement).download;
          origClick();
        };
      }
      return el;
    });

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(capturedDownload).toBe('hitchings-analisis.docx');
    });

    createElementSpy.mockRestore();
  });

  it('11 y 12. Mientras exporta, el botón muestra "Generando Word…" y previene doble click', async () => {
    let resolveExport: (val: any) => void;
    const exportPromise = new Promise((resolve) => {
      resolveExport = resolve;
    });
    const exportSpy = vi.spyOn(exportApi, 'exportAnalysisToWord').mockReturnValue(exportPromise as any);

    render(<AnalysisResult analysis={mockAnalysis} />);
    const btn = screen.getByRole('button', { name: /exportar a word/i });
    fireEvent.click(btn);
    fireEvent.click(btn); // Segundo click concurrente

    expect(btn).toBeDisabled();
    expect(screen.getByText(/generando word…/i)).toBeInTheDocument();
    expect(exportSpy).toHaveBeenCalledTimes(1);

    // Resolver exportación
    resolveExport!({ blob: new Blob(['']), filename: 'test.docx' });
    await waitFor(() => {
      expect(screen.queryByText(/generando word…/i)).not.toBeInTheDocument();
    });
  });

  it('13. Muestra feedback visual de éxito tras exportar a Word', async () => {
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockResolvedValue({
      blob: new Blob(['']),
      filename: 'test.docx',
    });

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(screen.getByText('Word generado correctamente')).toBeInTheDocument();
    });
  });

  it('14. Captura error genérico de exportación y lo muestra de forma amigable', async () => {
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockRejectedValue(new ApiError('Error servidor', 500));

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(
        screen.getByText('No se ha podido generar el archivo Word. Inténtalo de nuevo.')
      ).toBeInTheDocument();
    });
  });

  it('15. Mapea error HTTP 413 en exportación con mensaje explicativo de extensión', async () => {
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockRejectedValue(new ApiError('Payload too large', 413));

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(
        screen.getByText('El resultado es demasiado extenso para exportarlo a Word.')
      ).toBeInTheDocument();
    });
  });

  it('16. El resultado analítico en pantalla permanece intacto si la exportación falla', async () => {
    vi.spyOn(exportApi, 'exportAnalysisToWord').mockRejectedValue(new ApiError('Error de red', 500));

    render(<AnalysisResult analysis={mockAnalysis} />);
    fireEvent.click(screen.getByRole('button', { name: /exportar a word/i }));

    await waitFor(() => {
      expect(screen.getByText(/no se ha podido generar el archivo word/i)).toBeInTheDocument();
    });

    // El contenido sigue completamente visible
    expect(screen.getByText(mockAnalysis.title)).toBeInTheDocument();
    expect(screen.getByText(/1\. Cláusulas Clave/)).toBeInTheDocument();
  });

  it('17. Cambiar el contenido principal (texto) limpia el resultado previo', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue({ text: 'Texto 1', word_count: 2, character_count: 7 });
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysis);

    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/cargando catálogo/i)).not.toBeInTheDocument();
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/pega o escribe aquí/i);
    fireEvent.change(textarea, { target: { value: 'Texto inicial' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText(mockAnalysis.title)).toBeInTheDocument();
    });

    // Modificar el texto: debe limpiar el resultado
    fireEvent.change(textarea, { target: { value: 'Texto modificado' } });
    expect(screen.queryByText(mockAnalysis.title)).not.toBeInTheDocument();
  });

  it('18. Cambiar únicamente el prompt NO limpia el resultado inmediatamente', async () => {
    vi.spyOn(textApi, 'prepareText').mockResolvedValue({ text: 'Texto 1', word_count: 2, character_count: 7 });
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysis);

    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/cargando catálogo/i)).not.toBeInTheDocument();
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/pega o escribe aquí/i);
    fireEvent.change(textarea, { target: { value: 'Texto inicial' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText(mockAnalysis.title)).toBeInTheDocument();
    });

    // Cambiar de prompt sin cambiar texto
    const select = screen.getByLabelText(/tipo de análisis/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });

    // El resultado permanece en pantalla hasta que se ejecute nuevo análisis
    expect(screen.getByText(mockAnalysis.title)).toBeInTheDocument();
  });

  it('19. Un nuevo análisis sustituye limpiamente el resultado anterior', async () => {
    const analysis2: AnalysisResponse = {
      ...mockAnalysis,
      title: 'Resumen Ejecutivo Alfa',
      content: 'Nuevo contenido resumido.',
    };

    vi.spyOn(textApi, 'prepareText').mockResolvedValue({ text: 'Texto 1', word_count: 2, character_count: 7 });
    vi.spyOn(analysisApi, 'analyzeContent')
      .mockResolvedValueOnce(mockAnalysis)
      .mockResolvedValueOnce(analysis2);

    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/cargando catálogo/i)).not.toBeInTheDocument();
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/pega o escribe aquí/i);
    fireEvent.change(textarea, { target: { value: 'Texto inicial' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText(mockAnalysis.title)).toBeInTheDocument();
    });

    // Cambiar de prompt y reanalizar
    const select = screen.getByLabelText(/tipo de análisis/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(screen.getByText('Resumen Ejecutivo Alfa')).toBeInTheDocument();
      expect(screen.queryByText(mockAnalysis.title)).not.toBeInTheDocument();
    });
  });

  it('20. Invoca scroll suave al resultado al completarse el análisis', async () => {
    const scrollMock = vi.fn();
    window.HTMLElement.prototype.scrollIntoView = scrollMock;

    vi.spyOn(textApi, 'prepareText').mockResolvedValue({ text: 'Texto', word_count: 1, character_count: 5 });
    vi.spyOn(analysisApi, 'analyzeContent').mockResolvedValue(mockAnalysis);

    render(<App />);
    await waitFor(() => {
      expect(screen.queryByText(/cargando catálogo/i)).not.toBeInTheDocument();
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    fireEvent.change(screen.getByPlaceholderText(/pega o escribe aquí/i), { target: { value: 'Texto' } });
    fireEvent.click(screen.getByRole('button', { name: /analizar texto/i }));

    await waitFor(() => {
      expect(scrollMock).toHaveBeenCalledWith(
        expect.objectContaining({
          block: 'start',
        })
      );
    });
  });
});
