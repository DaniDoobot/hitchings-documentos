import { apiFetch } from './client';
import type {
  PromptSetting,
  PromptSettingUpdate,
  PromptOptionsGuidelines,
  EffectiveInstructionsRequest,
  EffectiveInstructionsResponse,
} from '../types/promptSettings';

/**
 * Obtiene el Prompt Base global de análisis vigente en PostgreSQL.
 * Accesible para cualquier usuario autenticado (admin y user).
 */
export async function getBasePrompt(): Promise<PromptSetting> {
  return apiFetch<PromptSetting>('/api/v1/prompt-settings/base');
}

/**
 * Actualiza el contenido del Prompt Base global en PostgreSQL.
 * Accesible para cualquier usuario autenticado (admin y user). Requiere CSRF.
 */
export async function updateBasePrompt(content: string): Promise<PromptSetting> {
  const payload: PromptSettingUpdate = { content };
  return apiFetch<PromptSetting>('/api/v1/prompt-settings/base', {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Obtiene las directivas transparentes de los modificadores de opciones (nivel de detalle y formato).
 */
export async function getOptionsGuidelines(): Promise<PromptOptionsGuidelines> {
  return apiFetch<PromptOptionsGuidelines>('/api/v1/prompt-settings/guidelines');
}

/**
 * Obtiene la composición transparente y desglosada de las instrucciones efectivas.
 */
export async function previewEffectiveInstructions(
  req: EffectiveInstructionsRequest,
): Promise<EffectiveInstructionsResponse> {
  return apiFetch<EffectiveInstructionsResponse>('/api/v1/prompt-settings/preview-instructions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(req),
  });
}
