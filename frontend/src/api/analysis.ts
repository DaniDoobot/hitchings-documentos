import { apiFetch } from './client';
import type { AnalysisRequest, AnalysisResponse } from '../types/api';

export async function analyzeContent(
  request: AnalysisRequest
): Promise<AnalysisResponse> {
  return await apiFetch<AnalysisResponse>('/api/v1/analysis', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
}
