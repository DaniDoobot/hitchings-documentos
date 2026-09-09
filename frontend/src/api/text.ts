import { apiFetch } from './client';
import type { TextPrepareResponse } from '../types/api';

export async function prepareText(text: string): Promise<TextPrepareResponse> {
  return await apiFetch<TextPrepareResponse>('/api/v1/text/prepare', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
}
