import React from 'react';
import { FileText, Mic, AlignLeft } from 'lucide-react';
import type { InputTab } from '../types/api';

interface InputTabsProps {
  activeTab: InputTab;
  onSelectTab: (tab: InputTab) => void;
}

export const InputTabs: React.FC<InputTabsProps> = ({
  activeTab,
  onSelectTab,
}) => {
  return (
    <nav className="tabs-nav" aria-label="Vías de entrada">
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'document'}
        className={`tab-btn ${activeTab === 'document' ? 'active' : ''}`}
        onClick={() => onSelectTab('document')}
      >
        <FileText size={18} />
        <span>Documento</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'audio'}
        className={`tab-btn ${activeTab === 'audio' ? 'active' : ''}`}
        onClick={() => onSelectTab('audio')}
      >
        <Mic size={18} />
        <span>Audio</span>
      </button>

      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'text'}
        className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
        onClick={() => onSelectTab('text')}
      >
        <AlignLeft size={18} />
        <span>Pegar texto</span>
      </button>
    </nav>
  );
};
