import { apiFetch } from './client';
import type {
  AnalysisType,
  AnalysisTypeListResponse,
  AnalysisTypeCreatePayload,
  AnalysisTypeUpdatePayload,
} from '../types/analysisTypes';

export type {
  AnalysisType,
  AnalysisTypeListResponse,
  AnalysisTypeCreatePayload,
  AnalysisTypeUpdatePayload,
};

/**
 * Obtiene el listado de tipos de análisis compartido por el despacho.
 * Accesible para cualquier usuario autenticado.
 */
export async function listAnalysisTypes(includeInactive: boolean = true): Promise<AnalysisTypeListResponse> {
  return apiFetch<AnalysisTypeListResponse>(`/api/v1/analysis-types?include_inactive=${includeInactive}`);
}

/**
 * Obtiene el detalle de un tipo de análisis específico por su UUID.
 */
export async function getAnalysisType(typeId: string): Promise<AnalysisType> {
  return apiFetch<AnalysisType>(`/api/v1/analysis-types/${typeId}`);
}

/**
 * Crea un nuevo tipo de análisis documental.
 * Accesible para cualquier usuario autenticado. Requiere CSRF.
 */
export async function createAnalysisType(payload: AnalysisTypeCreatePayload): Promise<AnalysisType> {
  return apiFetch<AnalysisType>('/api/v1/analysis-types', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

/**
 * Actualiza los datos o estado de un tipo de análisis.
 * Accesible para cualquier usuario autenticado. Requiere CSRF.
 */
export async function updateAnalysisType(
  typeId: string,
  payload: AnalysisTypeUpdatePayload,
): Promise<AnalysisType> {
  return apiFetch<AnalysisType>(`/api/v1/analysis-types/${typeId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}
