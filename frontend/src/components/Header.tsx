import React from 'react';
import { ShieldCheck } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="app-header">
      <div className="header-inner">
        <div className="header-branding">
          <img
            src="/favicon.png"
            alt="Hitchings y Gonzalez Documentos"
            className="brand-logo"
          />
          <div>
            <h1 className="brand-title">HITCHINGS Y GONZALEZ DOCUMENTOS</h1>
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
