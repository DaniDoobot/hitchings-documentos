import React, { useState } from 'react';
import { FileCode2, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AnalysisTypesManagement } from './AnalysisTypesManagement';
import { UsersManagement } from './UsersManagement';

interface SettingsViewProps {
  onTypesUpdated?: () => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ onTypesUpdated }) => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const [activeTab, setActiveTab] = useState<'analysis-types' | 'users'>('analysis-types');

  return (
    <div className="settings-container">
      <div className="settings-nav-bar" role="tablist" aria-label="Secciones de configuración">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'analysis-types'}
          className={`settings-tab-btn ${activeTab === 'analysis-types' ? 'active' : ''}`}
          onClick={() => setActiveTab('analysis-types')}
        >
          <FileCode2 size={16} />
          <span>Tipos de análisis</span>
        </button>

        {isAdmin && (
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'users'}
            className={`settings-tab-btn ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            <Users size={16} />
            <span>Usuarios</span>
          </button>
        )}
      </div>

      <div className="settings-tab-content">
        {activeTab === 'analysis-types' && (
          <AnalysisTypesManagement onTypesUpdated={onTypesUpdated} />
        )}
        {activeTab === 'users' && isAdmin && (
          <UsersManagement />
        )}
      </div>
    </div>
  );
};
