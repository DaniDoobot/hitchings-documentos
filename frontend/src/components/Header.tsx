import React from 'react';
import { ShieldCheck, LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const Header: React.FC = () => {
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

