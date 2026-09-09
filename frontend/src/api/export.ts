import { apiFetchBlob } from './client';

export interface WordExportMetadata {
  prompt_name?: string | null;
  model?: string | null;
}

export interface WordExportRequest {
  title: string;
  content: string;
  warnings: string[];
  metadata?: WordExportMetadata | null;
}

export interface WordExportResult {
  blob: Blob;
  filename: string;
}

export const DEFAULT_WORD_FILENAME = 'hitchings-analisis.docx';

export async function exportAnalysisToWord(
  request: WordExportRequest
): Promise<WordExportResult> {
  const { blob, filename } = await apiFetchBlob('/api/v1/export/word', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  return {
    blob,
    filename: filename || DEFAULT_WORD_FILENAME,
  };
}
