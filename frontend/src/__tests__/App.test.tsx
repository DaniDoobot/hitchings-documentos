import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as promptsApi from '../api/prompts';
import type { Prompt } from '../types/api';

const mockPrompts: Prompt[] = [
  {
    id: 'legal-analysis',
    name: 'Análisis Jurídico Integral',
    description: 'Dictamen exhaustivo de riesgos legales, obligaciones y contingencias.',
    instructions: 'Analiza el documento como jurista experto...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
  {
    id: 'executive-summary',
    name: 'Resumen Ejecutivo',
    description: 'Síntesis concisa de los puntos clave para toma de decisiones.',
    instructions: 'Genera un resumen ejecutivo de alto nivel...',
    is_active: true,
    is_system: true,
    created_at: '2026-09-08T10:00:00Z',
    updated_at: '2026-09-08T10:00:00Z',
  },
];

describe('HITCHINGS Documentos - Frontend Base (Bloque 6A)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const renderAppReady = async () => {
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue(mockPrompts);
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

  it('1. Renderiza el encabezado principal con la identidad corporativa de HITCHINGS', async () => {
    await renderAppReady();

    expect(screen.getByText(/HITCHINGS Y GONZALEZ DOCUMENTOS/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Procesamiento, Transcripción y Análisis Documental/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Sistema preparado/i)).toBeInTheDocument();
  });

  it('2. Permite alternar fluidamente entre las pestañas Documento, Audio y Pegar texto', async () => {
    await renderAppReady();

    const docTab = screen.getByRole('tab', { name: /documento/i });
    const audioTab = screen.getByRole('tab', { name: /audio/i });
    const textTab = screen.getByRole('tab', { name: /pegar texto/i });

    expect(docTab).toHaveClass('active');
    expect(
      screen.getByText(/Arrastra tu documento aquí/i)
    ).toBeInTheDocument();

    // Cambiar a Audio
    fireEvent.click(audioTab);
    expect(audioTab).toHaveClass('active');
    expect(screen.getByText(/Arrastra tu archivo de audio aquí/i)).toBeInTheDocument();
    expect(screen.getByText(/Modo de transcripción/i)).toBeInTheDocument();

    // Cambiar a Texto
    fireEvent.click(textTab);
    expect(textTab).toHaveClass('active');
    expect(
      screen.getByPlaceholderText(/Pega o escribe aquí el contenido documental/i)
    ).toBeInTheDocument();
  });

  it('3. Valida y acepta un documento permitido (.pdf)', async () => {
    await renderAppReady();

    const file = new File(['dummy content'], 'contrato.pdf', {
      type: 'application/pdf',
    });
    const input = screen.getByLabelText(/Cargar archivo de documento/i);

    await userEvent.upload(input, file);

    expect(screen.getByText('contrato.pdf')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('4. Muestra mensaje de error ante formato de documento no permitido (.exe, .png)', async () => {
    await renderAppReady();

    const invalidFile = new File(['bad'], 'script.exe', {
      type: 'application/x-msdownload',
    });
    const input = screen.getByLabelText(/Cargar archivo de documento/i);

    fireEvent.change(input, { target: { files: [invalidFile] } });

    expect(
      screen.getByText(/Formato no permitido. Solo se admiten archivos .pdf, .docx o .txt/i)
    ).toBeInTheDocument();
    expect(screen.queryByText('script.exe')).not.toBeInTheDocument();
  });

  it('5. Muestra mensaje de error cuando el documento supera el límite de 25 MB', async () => {
    await renderAppReady();

    const bigFile = new File(['content'], 'gran_documento.pdf', {
      type: 'application/pdf',
    });
    Object.defineProperty(bigFile, 'size', { value: 26 * 1024 * 1024 });

    const input = screen.getByLabelText(/Cargar archivo de documento/i);
    fireEvent.change(input, { target: { files: [bigFile] } });

    expect(
      screen.getByText(/El archivo supera el tamaño máximo permitido de 25 MB/i)
    ).toBeInTheDocument();
  });

  it('6. Permite eliminar un documento seleccionado mediante el botón de papelera', async () => {
    await renderAppReady();

    const file = new File(['test'], 'acta.docx', {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    });
    const input = screen.getByLabelText(/Cargar archivo de documento/i);
    await userEvent.upload(input, file);

    expect(screen.getByText('acta.docx')).toBeInTheDocument();

    const deleteBtn = screen.getByLabelText(/Eliminar documento seleccionado/i);
    fireEvent.click(deleteBtn);

    expect(screen.queryByText('acta.docx')).not.toBeInTheDocument();
    expect(screen.getByText(/Arrastra tu documento aquí/i)).toBeInTheDocument();
  });

  it('7. Valida y acepta un archivo de audio permitido (.mp3, .wav)', async () => {
    await renderAppReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));

    const audioFile = new File(['audio raw data'], 'grabacion.mp3', {
      type: 'audio/mpeg',
    });
    const input = screen.getByLabelText(/Cargar archivo de audio/i);
    await userEvent.upload(input, audioFile);

    expect(screen.getByText('grabacion.mp3')).toBeInTheDocument();
  });

  it('8. Muestra mensaje de error cuando el audio supera los 200 MB', async () => {
    await renderAppReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));

    const hugeAudio = new File(['audio'], 'audiencia.wav', { type: 'audio/wav' });
    Object.defineProperty(hugeAudio, 'size', { value: 205 * 1024 * 1024 });

    const input = screen.getByLabelText(/Cargar archivo de audio/i);
    fireEvent.change(input, { target: { files: [hugeAudio] } });

    expect(
      screen.getByText(/El archivo de audio supera el tamaño máximo permitido de 200 MB/i)
    ).toBeInTheDocument();
  });

  it('9. En pestaña de audio, el modo inteligente (smart) deshabilita la diarización con aviso explicativo', async () => {
    await renderAppReady();

    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));

    const diarizationCheckbox = screen.getByLabelText(
      /Activar diarización/i
    ) as HTMLInputElement;

    // En verbatim está habilitado
    expect(diarizationCheckbox).not.toBeDisabled();

    // Cambiar a Normalizado (Smart)
    const smartRadio = screen.getByLabelText(/Normalizado \(Smart\)/i);
    fireEvent.click(smartRadio);

    // Ahora la diarización debe estar deshabilitada
    expect(diarizationCheckbox).toBeDisabled();
    expect(diarizationCheckbox.checked).toBe(false);
    expect(
      screen.getByText(/La diarización no está disponible en modo inteligente/i)
    ).toBeInTheDocument();

    // Volver a Literal (Verbatim)
    const verbatimRadio = screen.getByLabelText(/Literal \(Verbatim\)/i);
    fireEvent.click(verbatimRadio);
    expect(diarizationCheckbox).not.toBeDisabled();
  });

  it('10. En pestaña de texto, actualiza en tiempo real el conteo de caracteres y palabras', async () => {
    await renderAppReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));

    const textarea = screen.getByPlaceholderText(/Pega o escribe aquí el contenido/i);
    await userEvent.type(textarea, 'Este es un texto de prueba.');

    expect(screen.getByText(/palabras/i)).toHaveTextContent('6 palabras');
    expect(screen.getByText(/27/i)).toBeInTheDocument(); // 27 caracteres
  });

  it('11. Permite vaciar el contenido del textarea mediante el botón Limpiar', async () => {
    await renderAppReady();

    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));

    const textarea = screen.getByPlaceholderText(/Pega o escribe aquí el contenido/i);
    await userEvent.type(textarea, 'Texto temporal');

    const clearBtn = screen.getByTitle(/Limpiar texto/i);
    fireEvent.click(clearBtn);

    expect(textarea).toHaveValue('');
    expect(screen.getByText(/palabras/i)).toHaveTextContent('0 palabras');
  });

  it('12. Carga y muestra los prompts disponibles desde la API, preseleccionando el primero', async () => {
    await renderAppReady();

    expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    expect(
      screen.getByText(/Dictamen exhaustivo de riesgos legales/i)
    ).toBeInTheDocument();
  });

  it('13. Muestra estado de carga mientras se solicita el catálogo de prompts', async () => {
    let resolvePrompts: (value: Prompt[]) => void;
    const pendingPromise = new Promise<Prompt[]>((resolve) => {
      resolvePrompts = resolve;
    });
    vi.spyOn(promptsApi, 'fetchPrompts').mockReturnValue(pendingPromise);

    render(<App />);

    await waitFor(() => {
      expect(
        screen.getByText(/Cargando catálogo de análisis.../i)
      ).toBeInTheDocument();
    });

    resolvePrompts!(mockPrompts);

    await waitFor(() => {
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });
  });

  it('14. Gestiona error en la carga de prompts y permite reintentar', async () => {
    const fetchSpy = vi
      .spyOn(promptsApi, 'fetchPrompts')
      .mockRejectedValueOnce(new Error('Fallo de conexión al backend'))
      .mockResolvedValueOnce(mockPrompts);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText(/Fallo de conexión al backend/i)).toBeInTheDocument();
    });

    const retryBtn = screen.getByRole('button', { name: /reintentar/i });
    fireEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByDisplayValue(/Análisis Jurídico Integral/i)).toBeInTheDocument();
    });

    expect(fetchSpy).toHaveBeenCalledTimes(2);
  });

  it('15. Al cambiar el prompt seleccionado, se actualiza la previsualización descriptiva', async () => {
    await renderAppReady();

    const select = screen.getByLabelText(/Tipo de análisis \(Prompt\)/i);
    fireEvent.change(select, { target: { value: 'executive-summary' } });

    expect(
      screen.getByText(/Síntesis concisa de los puntos clave/i)
    ).toBeInTheDocument();
  });

  it('16. Permite modificar las opciones de nivel de profundidad y estructura de salida', async () => {
    await renderAppReady();

    const briefOption = screen.getByRole('button', { name: /resumido/i });
    const detailedOption = screen.getByRole('button', { name: /detallado/i });

    expect(screen.getByRole('button', { name: /estándar/i })).toHaveClass('active');

    fireEvent.click(detailedOption);
    expect(detailedOption).toHaveClass('active');

    fireEvent.click(briefOption);
    expect(briefOption).toHaveClass('active');

    // Estructura de salida
    const bulletOption = screen.getByRole('button', { name: /puntos clave/i });
    fireEvent.click(bulletOption);
    expect(bulletOption).toHaveClass('active');
  });

  it('17. El botón principal de análisis adapta dinámicamente su etiqueta a la vía activa', async () => {
    await renderAppReady();

    // Tab Documento
    expect(screen.getByRole('button', { name: /analizar documento/i })).toBeInTheDocument();

    // Tab Audio
    fireEvent.click(screen.getByRole('tab', { name: /audio/i }));
    expect(
      screen.getByRole('button', { name: /transcribir y analizar/i })
    ).toBeInTheDocument();

    // Tab Texto
    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    expect(screen.getByRole('button', { name: /analizar texto/i })).toBeInTheDocument();
  });

  it('18. El botón principal permanece deshabilitado hasta contar con contenido y prompt', async () => {
    await renderAppReady();

    const ctaBtn = screen.getByRole('button', { name: /analizar documento/i });
    expect(ctaBtn).toBeDisabled();

    // Cargar documento
    const file = new File(['dummy'], 'informe.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText(/Cargar archivo de documento/i), file);

    // Ahora tiene documento y prompt preseleccionado -> debe habilitarse
    expect(ctaBtn).not.toBeDisabled();

    // Si eliminamos el documento, vuelve a deshabilitarse
    fireEvent.click(screen.getByLabelText(/Eliminar documento seleccionado/i));
    expect(ctaBtn).toBeDisabled();
  });

  it('19. Preserva el contenido ingresado al navegar entre pestañas', async () => {
    await renderAppReady();

    // Ir a pestaña de texto y escribir
    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));
    const textarea = screen.getByPlaceholderText(/Pega o escribe aquí el contenido/i);
    await userEvent.type(textarea, 'Texto que no debe perderse.');

    // Cambiar a Documento y luego volver a Texto
    fireEvent.click(screen.getByRole('tab', { name: /documento/i }));
    fireEvent.click(screen.getByRole('tab', { name: /pegar texto/i }));

    expect(
      screen.getByDisplayValue('Texto que no debe perderse.')
    ).toBeInTheDocument();
  });
});
