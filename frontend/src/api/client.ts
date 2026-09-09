export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    let errorMessage = `Error HTTP ${response.status}: ${response.statusText}`;
    let errorData: unknown = null;

    try {
      errorData = await response.json();
      if (
        errorData &&
        typeof errorData === 'object' &&
        'detail' in errorData &&
        typeof (errorData as { detail: unknown }).detail === 'string'
      ) {
        errorMessage = (errorData as { detail: string }).detail;
      }
    } catch {
      // Si la respuesta no es JSON, conservar el mensaje HTTP por defecto
    }

    throw new ApiError(errorMessage, response.status, errorData);
  }

  return (await response.json()) as T;
}
