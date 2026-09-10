import React from 'react';
import { ShieldCheck, LogOut, User as UserIcon, Settings, FileText } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  activeSection?: 'analysis' | 'settings';
  onSelectSection?: (section: 'analysis' | 'settings') => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeSection = 'analysis',
  onSelectSection,
}) => {
  const { user, logout } = useAuth();


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

        {user && onSelectSection && (
          <nav className="header-nav" aria-label="Navegación principal">
            <button
              type="button"
              className={`header-nav-btn ${activeSection === 'analysis' ? 'active' : ''}`}
              onClick={() => onSelectSection('analysis')}
              aria-current={activeSection === 'analysis' ? 'page' : undefined}
            >
              <FileText size={15} />
              <span>Análisis</span>
            </button>
            <button
              type="button"
              className={`header-nav-btn ${activeSection === 'settings' ? 'active' : ''}`}
              onClick={() => onSelectSection('settings')}
              aria-current={activeSection === 'settings' ? 'page' : undefined}
            >
              <Settings size={15} />
              <span>Configuración</span>
            </button>
          </nav>
        )}

        <div className="header-right">
          <div className="header-status">
            <ShieldCheck size={14} color="#22c55e" />
            <span>Sistema preparado</span>
            <span className="status-dot"></span>
          </div>

          {user && (
            <div className="header-user-badge">
              <span className="header-user-email" title={user.email}>
                <UserIcon size={14} className="user-badge-icon" />
                {user.email}
              </span>
              <button
                type="button"
                onClick={logout}
                className="header-logout-btn"
                title="Cerrar sesión"
                aria-label="Cerrar sesión"
              >
                <LogOut size={14} />
                <span>Cerrar sesión</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
