import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch } from '../api/client';
import { fetchPrompts, fetchPromptById } from '../api/prompts';

describe('API Client y Prompts Service', () => {
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
});
