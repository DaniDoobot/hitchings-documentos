import { ApiError } from '../api/client';
import type { InputTab, ProcessingStage } from '../types/api';

export function getFriendlyErrorMessage(
  error: unknown,
  stage: ProcessingStage,
  avenue: InputTab
): string {
  if (error instanceof ApiError) {
    if (error.status === 413) {
      if (stage === 'extracting') {
        return 'El documento supera el tamaño permitido.';
      }
      if (stage === 'transcribing') {
        return 'El archivo de audio supera el tamaño permitido.';
      }
      if (stage === 'preparing') {
        return 'El texto supera el límite permitido.';
      }
      if (stage === 'analyzing') {
        return 'El contenido es demasiado extenso para analizarlo en una sola operación.';
      }
    }

    if (error.status === 415) {
      return 'El formato seleccionado no está soportado.';
    }

    if (error.status >= 502 && error.status <= 504) {
      return 'El servicio de análisis no está disponible temporalmente. Inténtalo de nuevo.';
    }

    if (error.status === 400) {
      // Si el mensaje del backend es limpio y seguro
      if (
        error.message &&
        !error.message.includes('Traceback') &&
        !error.message.includes('Exception') &&
        !error.message.startsWith('Error HTTP')
      ) {
        return error.message;
      }
      return 'No se ha podido procesar el contenido enviado.';
    }

    // Para 500 o fallos de servidor, saltar a los mensajes amigables por etapa
    if (error.status === 500) {
      // Dejar caer a los fallbacks por etapa más abajo
    } else if (
      error.message &&
      !error.message.includes('Traceback') &&
      !error.message.includes('Exception') &&
      !error.message.startsWith('Error HTTP')
    ) {
      return error.message;
    }
  }

  if (error instanceof Error) {
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      return 'No se pudo establecer conexión con el backend. Verifica que el servidor está en ejecución.';
    }
  }

  // Fallbacks por etapa
  if (stage === 'extracting') {
    return 'No se ha podido extraer el contenido del documento.';
  }
  if (stage === 'transcribing') {
    return 'No se ha podido transcribir la grabación de audio.';
  }
  if (stage === 'preparing') {
    return 'No se ha podido preparar el texto para su análisis.';
  }
  if (stage === 'analyzing') {
    if (avenue === 'audio') {
      return 'La transcripción se completó, pero no se pudo realizar el análisis.';
    }
    if (avenue === 'document') {
      return 'El documento se leyó correctamente, pero falló el análisis con el modelo de IA.';
    }
    return 'Ocurrió un fallo durante el análisis del contenido.';
  }

  return 'Ocurrió un error inesperado durante el procesamiento.';
}
