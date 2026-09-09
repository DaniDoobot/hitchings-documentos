export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? ''
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

export interface BlobResponse {
  blob: Blob;
  filename?: string;
}

export async function apiFetchBlob(
  endpoint: string,
  options?: RequestInit
): Promise<BlobResponse> {
  const url = `${API_BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
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

  const contentDisposition = response.headers.get('Content-Disposition') || '';
  let filename: string | undefined;

  // Intentar parsear filename*=UTF-8''... o filename="..."
  const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (filenameStarMatch && filenameStarMatch[1]) {
    try {
      filename = decodeURIComponent(filenameStarMatch[1]);
    } catch {
      filename = filenameStarMatch[1];
    }
  } else {
    const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
    if (filenameMatch && filenameMatch[1]) {
      filename = filenameMatch[1].trim();
    }
  }

  // Sanitizar filename: asegurar que sea únicamente un nombre de archivo, nunca un path
  if (filename) {
    filename = filename.replace(/^.*[\\/]/, '');
  }

  const blob = await response.blob();
  return { blob, filename };
}

