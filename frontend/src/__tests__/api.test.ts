import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from '../api/client';
import { fetchPrompts, fetchPromptById } from '../api/prompts';
import { extractDocument } from '../api/documents';
import { transcribeAudio } from '../api/audio';
import { prepareText } from '../api/text';
import { analyzeContent } from '../api/analysis';

describe('API Client y Servicios', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('apiFetch maneja respuestas JSON exitosas', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'ok' }),
    } as Response);

    const result = await apiFetch<{ status: string }>('/health');
    expect(result).toEqual({ status: 'ok' });
  });

  it('apiFetch lanza ApiError con detalle ante errores HTTP', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Formato no admitido' }),
    } as Response);

    await expect(apiFetch('/endpoint')).rejects.toThrow('Formato no admitido');
  });

  it('fetchPrompts realiza petición GET a /api/v1/prompts', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        prompts: [{ id: 'p1', name: 'Test' }],
        total: 1,
      }),
    } as Response);

    const prompts = await fetchPrompts();
    expect(prompts).toEqual([{ id: 'p1', name: 'Test' }]);
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/prompts'),
      expect.anything()
    );
  });

  it('fetchPromptById realiza petición GET con el id codificado', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: 'legal-analysis', name: 'Legal' }),
    } as Response);

    const prompt = await fetchPromptById('legal-analysis');
    expect(prompt.id).toBe('legal-analysis');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/prompts/legal-analysis'),
      expect.anything()
    );
  });

  it('extractDocument envía FormData a /api/v1/documents/extract', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        filename: 'test.pdf',
        extension: 'pdf',
        content_type: 'application/pdf',
        size_bytes: 100,
        page_count: 1,
        word_count: 10,
        character_count: 50,
        text: 'Texto extraído',
        warnings: [],
      }),
    } as Response);

    const dummyFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });
    const response = await extractDocument(dummyFile);

    expect(response.text).toBe('Texto extraído');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/documents/extract'),
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
  });

  it('transcribeAudio envía query params y FormData a /api/v1/audio/transcribe', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        filename: 'test.mp3',
        extension: 'mp3',
        content_type: 'audio/mpeg',
        size_bytes: 100,
        transcription_model: 'gemini-3.5-transcribe',
        mode: 'verbatim',
        diarization: true,
        text: 'Texto transcrito',
        word_count: 10,
        character_count: 50,
        segments: [],
        warnings: [],
      }),
    } as Response);

    const dummyAudio = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' });
    const response = await transcribeAudio(dummyAudio, 'verbatim', true);

    expect(response.text).toBe('Texto transcrito');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/audio/transcribe?mode=verbatim&diarization=true'),
      expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData),
      })
    );
  });

  it('transcribeAudio fuerza diarization=false si mode es smart', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        filename: 'test.mp3',
        extension: 'mp3',
        content_type: 'audio/mpeg',
        size_bytes: 100,
        transcription_model: 'gemini-3.5-transcribe',
        mode: 'smart',
        diarization: false,
        text: 'Texto smart',
        word_count: 5,
        character_count: 25,
        segments: [],
        warnings: [],
      }),
    } as Response);

    const dummyAudio = new File(['audio'], 'test.mp3', { type: 'audio/mpeg' });
    await transcribeAudio(dummyAudio, 'smart', true);

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/audio/transcribe?mode=smart&diarization=false'),
      expect.anything()
    );
  });

  it('prepareText envía JSON a /api/v1/text/prepare', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        text: 'Texto normalizado',
        word_count: 2,
        character_count: 17,
      }),
    } as Response);

    const response = await prepareText('Texto normalizado');
    expect(response.text).toBe('Texto normalizado');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/text/prepare'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ text: 'Texto normalizado' }),
      })
    );
  });

  it('analyzeContent envía JSON a /api/v1/analysis', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        prompt_id: 'p1',
        prompt_name: 'Análisis Legal',
        model: 'gemini-3.8-flash',
        options: { detail_level: 'standard', output_format: 'sections' },
        title: 'Resultado',
        content: '# Resumen',
        warnings: [],
        usage: { input_tokens: 100, output_tokens: 50, total_tokens: 150 },
      }),
    } as Response);

    const req = {
      text: 'Doc text',
      prompt_id: 'p1',
      options: { detail_level: 'standard' as const, output_format: 'sections' as const },
    };
    const response = await analyzeContent(req);

    expect(response.title).toBe('Resultado');
    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/analysis'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(req),
      })
    );
  });
});
