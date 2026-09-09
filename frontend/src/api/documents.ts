import { apiFetch } from './client';
import type { DocumentExtractResponse } from '../types/api';

export async function extractDocument(
  file: File
): Promise<DocumentExtractResponse> {
  const formData = new FormData();
  formData.append('file', file);

  return await apiFetch<DocumentExtractResponse>('/api/v1/documents/extract', {
    method: 'POST',
    body: formData,
  });
}
