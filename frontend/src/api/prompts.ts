import { apiFetch } from './client';
import type { Prompt, PromptListResponse } from '../types/api';

export async function fetchPrompts(includeInactive = false): Promise<Prompt[]> {
  const query = includeInactive ? '?include_inactive=true' : '';
  const response = await apiFetch<PromptListResponse>(`/api/v1/prompts${query}`);
  return response.prompts;
}

export async function fetchPromptById(promptId: string): Promise<Prompt> {
  return await apiFetch<Prompt>(`/api/v1/prompts/${encodeURIComponent(promptId)}`);
}
