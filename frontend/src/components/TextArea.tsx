import React from 'react';
import { Trash2 } from 'lucide-react';

const MAX_TEXT_CHARACTERS = 5000000;

interface TextAreaProps {
  text: string;
  onTextChange: (text: string) => void;
}

export const TextArea: React.FC<TextAreaProps> = ({ text, onTextChange }) => {
  const calculateWordCount = (str: string): number => {
    const trimmed = str.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  };

  const wordCount = calculateWordCount(text);
  const charCount = text.length;

  return (
    <div className="textarea-wrapper">
      <textarea
        className="custom-textarea"
        placeholder="Pega o escribe aquí el contenido documental a analizar..."
        value={text}
        onChange={(e) => {
          if (e.target.value.length <= MAX_TEXT_CHARACTERS) {
            onTextChange(e.target.value);
          }
        }}
        maxLength={MAX_TEXT_CHARACTERS}
        aria-label="Contenido documental en texto"
      />

      <div className="textarea-footer">
        <div style={{ display: 'flex', gap: '1rem' }}>
          <span>
            <strong>{charCount.toLocaleString()}</strong> / {MAX_TEXT_CHARACTERS.toLocaleString()} caracteres
          </span>
          <span>•</span>
          <span>
            <strong>{wordCount.toLocaleString()}</strong> palabras
          </span>
        </div>

        {text.length > 0 && (
          <button
            type="button"
            className="btn-secondary-sm"
            onClick={() => onTextChange('')}
            title="Limpiar texto"
          >
            <Trash2 size={12} style={{ display: 'inline', marginRight: '4px', verticalAlign: 'middle' }} />
            Limpiar
          </button>
        )}
      </div>
    </div>
  );
};
