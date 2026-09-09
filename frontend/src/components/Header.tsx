import React from 'react';
import { FileText, ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="header-branding">
          <div className="brand-icon">
            <FileText size={22} color="#93c5fd" />
          </div>
          <div>
            <h1 className="brand-title">HITCHINGS DOCUMENTOS</h1>
            <p className="brand-subtitle">
              Procesamiento, Transcripción y Análisis Documental
            </p>
          </div>
        </div>

        <div className="header-status">
          <ShieldCheck size={14} color="#22c55e" />
          <span>Sistema preparado</span>
          <span className="status-dot"></span>
        </div>
      </div>
    </header>
  );
};
