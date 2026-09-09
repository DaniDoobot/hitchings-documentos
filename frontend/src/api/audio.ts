import { apiFetch } from './client';
import type { AudioTranscribeResponse, TranscriptionMode } from '../types/api';

export async function transcribeAudio(
  file: File,
  mode: TranscriptionMode = 'verbatim',
  diarization: boolean = false
): Promise<AudioTranscribeResponse> {
  // Comprobación defensiva: nunca permitir diarization=true si mode='smart'
  const effectiveDiarization = mode === 'smart' ? false : Boolean(diarization);

  const queryParams = new URLSearchParams({
    mode,
    diarization: String(effectiveDiarization),
  });

  const formData = new FormData();
  formData.append('file', file);

  return await apiFetch<AudioTranscribeResponse>(
    `/api/v1/audio/transcribe?${queryParams.toString()}`,
    {
      method: 'POST',
      body: formData,
    }
  );
}
