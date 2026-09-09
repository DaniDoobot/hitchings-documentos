import React, { useRef, useState } from 'react';
import { UploadCloud, File, Trash2, AlertCircle } from 'lucide-react';

const MAX_DOCUMENT_SIZE_BYTES = 25 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.txt'];

interface DocumentAreaProps {
  selectedFile: File | null;
  onFileSelect: (file: File | null) => void;
  error: string | null;
  onError: (error: string | null) => void;
}

export const DocumentArea: React.FC<DocumentAreaProps> = ({
  selectedFile,
  onFileSelect,
  error,
  onError,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const validateAndSetFile = (file: File) => {
    onError(null);

    const fileNameLower = file.name.toLowerCase();
    const isAllowedExt = ALLOWED_EXTENSIONS.some((ext) =>
      fileNameLower.endsWith(ext)
    );

    if (!isAllowedExt) {
      onError(
        'Formato no permitido. Solo se admiten archivos .pdf, .docx o .txt'
      );
      return;
    }

    if (file.size > MAX_DOCUMENT_SIZE_BYTES) {
      onError('El archivo supera el tamaño máximo permitido de 25 MB');
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

  return (
    <div className="document-area">
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
            accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            style={{ display: 'none' }}
            aria-label="Cargar archivo de documento"
          />
          <div className="dropzone-icon">
            <UploadCloud size={40} />
          </div>
          <p className="dropzone-title">
            Arrastra tu documento aquí o haz clic para seleccionarlo
          </p>
          <p className="dropzone-hint">
            Formatos admitidos: PDF, DOCX, TXT (Máximo 25 MB)
          </p>
        </div>
      ) : (
        <div className="file-info-badge">
          <div className="file-info-details">
            <File size={28} color="#2563eb" />
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
            aria-label="Eliminar documento seleccionado"
            title="Eliminar documento"
          >
            <Trash2 size={18} />
          </button>
        </div>
      )}
    </div>
  );
};
