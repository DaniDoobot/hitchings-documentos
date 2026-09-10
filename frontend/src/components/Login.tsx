import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, Loader2, AlertCircle } from 'lucide-react';

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login({ email, password });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage('Email o contraseña incorrectos.');
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <img
            src="/favicon.png"
            alt="Hitchings y Gonzalez Documentos"
            className="login-logo"
          />
          <h1 className="login-title">HITCHINGS Y GONZALEZ DOCUMENTOS</h1>
          <p className="login-subtitle">Acceso a la plataforma</p>
        </div>

        {errorMessage && (
          <div className="login-error-alert" role="alert">
            <AlertCircle size={18} className="login-error-icon" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="email" className="login-label">
              Correo electrónico
            </label>
            <div className="login-input-wrapper">
              <Mail size={18} className="login-input-icon" />
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                placeholder="usuario@ejemplo.com"
                className="login-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className="login-field">
            <label htmlFor="password" className="login-label">
              Contraseña
            </label>
            <div className="login-input-wrapper">
              <Lock size={18} className="login-input-icon" />
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                placeholder="••••••••••••"
                className="login-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <button
            type="submit"
            className="login-submit-button"
            disabled={isSubmitting || !email || !password}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="login-spinner" />
                <span>Iniciando sesión...</span>
              </>
            ) : (
              'Iniciar sesión'
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
