import React, { useEffect, useRef, useState } from 'react';
import { UploadCloud, Music, Video, Trash2, AlertCircle } from 'lucide-react';
import type { TranscriptionMode } from '../types/api';

const MAX_AUDIO_SIZE_BYTES = 1024 * 1024 * 1024; // 1 GB
const ALLOWED_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac', '.webm', '.mp4'];

interface AudioAreaProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  error: string | null;
  onError: (error: string | null) => void;
  mode: TranscriptionMode;
  onModeChange: (mode: TranscriptionMode) => void;
  diarization: boolean;
  onDiarizationChange: (diarization: boolean) => void;
}

export const AudioArea: React.FC<AudioAreaProps> = ({
  selectedFile,
  onFileSelect,
  error,
  onError,
  mode,
  onModeChange,
  diarization,
  onDiarizationChange,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isVideo = Boolean(
    selectedFile && selectedFile.name.toLowerCase().endsWith('.mp4')
  );

  useEffect(() => {
    if (isVideo && selectedFile) {
      const url = URL.createObjectURL(selectedFile);
      setVideoUrl(url);
      return () => {
        URL.revokeObjectURL(url);
        setVideoUrl(null);
      };
    } else {
      setVideoUrl(null);
    }
  }, [isVideo, selectedFile]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
    return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  };

  const validateAndSetFile = (file: File) => {
    onError(null);

    const fileNameLower = file.name.toLowerCase();
    const isAllowedExt = ALLOWED_EXTENSIONS.some((ext) =>
      fileNameLower.endsWith(ext)
    );

    if (!isAllowedExt) {
      onError(
        'Formato no permitido. Solo se admiten archivos .mp3, .wav, .m4a, .aac, .ogg, .flac, .webm o .mp4'
      );
      return;
    }

    if (file.size > MAX_AUDIO_SIZE_BYTES) {
      onError('El archivo supera el tamaño máximo permitido de 1 GB');
      return;
    }

    onFileSelect(file);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemove = () => {
    onFileSelect(null);
    onError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleModeSelection = (newMode: TranscriptionMode) => {
    onModeChange(newMode);
    if (newMode === 'smart') {
      onDiarizationChange(false);
    }
  };

  return (
    <div className="audio-area">
      {error && (
        <div className="banner banner-danger" role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        </div>
      )}

      {!selectedFile ? (
        <div
          className={`dropzone ${isDragActive ? 'drag-active' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              fileInputRef.current?.click();
            }
          }}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleInputChange}
            accept=".mp3,.wav,.m4a,.aac,.ogg,.flac,.webm,.mp4,audio/*,video/mp4"
            style={{ display: 'none' }}
            aria-label="Cargar archivo de audio o vídeo"
          />
          <div className="dropzone-icon">
            <UploadCloud size={40} />
          </div>
          <p className="dropzone-title">
            Arrastra tu archivo de audio aquí o haz clic para seleccionarlo
          </p>
          <p className="dropzone-hint">
            Formatos admitidos: MP3, WAV, M4A, AAC, OGG, FLAC, WEBM, MP4 (Máximo 1 GB)
          </p>
        </div>
      ) : isVideo ? (
        <div className="file-info-badge file-info-video">
          <div className="video-preview-wrapper">
            <video
              controls
              className="video-preview-player"
              src={videoUrl || undefined}
              aria-label="Previsualización de vídeo"
            >
              Tu navegador no soporta la reproducción de este vídeo.
            </video>
          </div>
          <div className="file-info-video-footer">
            <div className="file-info-details">
              <Video size={24} color="#2563eb" />
              <div>
                <p className="file-name" title={selectedFile.name}>
                  {selectedFile.name}
                </p>
                <p className="file-size">{formatFileSize(selectedFile.size)}</p>
              </div>
            </div>
            <button
              type="button"
              className="btn-remove"
              onClick={handleRemove}
              aria-label="Eliminar vídeo seleccionado"
              title="Eliminar vídeo"
            >
              <Trash2 size={18} />
            </button>
          </div>
        </div>
      ) : (
        <div className="file-info-badge">
          <div className="file-info-details">
            <Music size={28} color="#2563eb" />
            <div>
              <p className="file-name" title={selectedFile.name}>
                {selectedFile.name}
              </p>
              <p className="file-size">{formatFileSize(selectedFile.size)}</p>
            </div>
          </div>
          <button
            type="button"
            className="btn-remove"
            onClick={handleRemove}
            aria-label="Eliminar audio seleccionado"
            title="Eliminar audio"
          >
            <Trash2 size={18} />
          </button>
        </div>
      )}

      <div className="audio-controls">
        <div>
          <p className="control-group-title">Modo de transcripción</p>
          <div className="radio-group">
            <label className="radio-label">
              <input
                type="radio"
                name="transcriptionMode"
                value="verbatim"
                checked={mode === 'verbatim'}
                onChange={() => handleModeSelection('verbatim')}
              />
              <span>Literal (Verbatim)</span>
            </label>
            <label className="radio-label">
              <input
                type="radio"
                name="transcriptionMode"
                value="smart"
                checked={mode === 'smart'}
                onChange={() => handleModeSelection('smart')}
              />
              <span>Normalizado (Smart)</span>
            </label>
          </div>
          <p className="field-help">
            {mode === 'verbatim'
              ? 'Transcribe fielmente cada palabra y vacilación hablada.'
              : 'Corrige muletillas, repeticiones y normaliza la redacción para lectura fluida.'}
          </p>
        </div>

        <div>
          <p className="control-group-title">Identificación de intervinientes</p>
          <label
            className={`checkbox-label ${mode === 'smart' ? 'disabled' : ''}`}
          >
            <input
              type="checkbox"
              checked={diarization}
              disabled={mode === 'smart'}
              onChange={(e) => onDiarizationChange(e.target.checked)}
              aria-describedby="diarization-help"
            />
            <span>Activar diarización (diferenciación de interlocutores)</span>
          </label>
          {mode === 'smart' ? (
            <p id="diarization-help" className="field-help" style={{ color: '#d97706' }}>
              La diarización no está disponible en modo inteligente
            </p>
          ) : (
            <p id="diarization-help" className="field-help">
              Identifica cambios de voz y etiqueta a cada interviniente.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
