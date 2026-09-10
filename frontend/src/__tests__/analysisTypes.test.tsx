import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as authApi from '../api/auth';
import * as promptsApi from '../api/prompts';
import * as analysisTypesApi from '../api/analysisTypes';
import type { UserPublic } from '../types/auth';
import type { AnalysisType } from '../types/analysisTypes';

const mockAdminUser: UserPublic = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'admin@hitchings-gonzalez.com',
  role: 'admin',
  is_active: true,
  created_at: '2026-09-08T10:00:00Z',
  updated_at: '2026-09-08T10:00:00Z',
  last_login_at: '2026-09-08T10:00:00Z',
};

const mockRegularUser: UserPublic = {
  id: '22222222-2222-2222-2222-222222222222',
  email: 'abogado@hitchings-gonzalez.com',
  role: 'user',
  is_active: true,
  created_at: '2026-09-09T10:00:00Z',
  updated_at: '2026-09-09T10:00:00Z',
  last_login_at: '2026-09-09T12:00:00Z',
};

const mockAnalysisTypes: AnalysisType[] = [
  {
    id: 'a1000000-0000-0000-0000-000000000001',
    code: 'executive-summary',
    name: 'Resumen ejecutivo',
    description: 'Síntesis clara y estructurada del documento.',
    instructions: 'Eres un asistente experto en síntesis documental...',
    is_active: true,
    created_by_user_id: null,
    updated_by_user_id: null,
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
  },
  {
    id: 'a1000000-0000-0000-0000-000000000002',
    code: 'legal-analysis',
    name: 'Análisis jurídico',
    description: 'Examen de partes, pretensiones y fundamentos de derecho.',
    instructions: 'Eres un asistente jurídico especializado en análisis riguroso...',
    is_active: true,
    created_by_user_id: null,
    updated_by_user_id: null,
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
  },
];

describe('Tipos de Análisis Dinámicos y Base Estructural (Bloque 7C)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue([]);
    vi.spyOn(analysisTypesApi, 'listAnalysisTypes').mockResolvedValue({
      items: mockAnalysisTypes,
      total: mockAnalysisTypes.length,
    });
  });

  it('1. Usuario normal (role=user) tiene acceso visible a Configuración', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });
  });

  it('2. Usuario normal en Configuración ve únicamente la pestaña "Tipos de análisis"', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /usuarios/i })).not.toBeInTheDocument();
    });
  });

  it('3. Administrador en Configuración ve ambas pestañas ("Tipos de análisis" y "Usuarios")', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /usuarios/i })).toBeInTheDocument();
    });
  });

  it('4. Muestra banner informativo sobre la Base Estructural Jurídica inmutable', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));

    await waitFor(() => {
      expect(screen.getByText(/Base Estructural Jurídica de HITCHINGS & GONZÁLEZ \(Inmutable\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Derecho de la Competencia \(antitrust\)/i)).toBeInTheDocument();
    });
  });

  it('5. Carga y visualiza la tabla con los tipos de análisis y sus códigos estables', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));

    await waitFor(() => {
      expect(screen.getByText('Resumen ejecutivo')).toBeInTheDocument();
      expect(screen.getByText('executive-summary')).toBeInTheDocument();
      expect(screen.getByText('Análisis jurídico')).toBeInTheDocument();
      expect(screen.getByText('legal-analysis')).toBeInTheDocument();
    });
  });

  it('6. Crea un nuevo tipo de análisis exitosamente', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const createSpy = vi.spyOn(analysisTypesApi, 'createAnalysisType').mockResolvedValue({
      id: 'a1000000-0000-0000-0000-000000000099',
      code: 'analisis-carteles',
      name: 'Análisis de Cárteles',
      description: 'Detección y examen de indicios de colusión.',
      instructions: 'Instrucciones especializadas sobre cárteles e infracciones del art. 101 TFUE.',
      is_active: true,
      created_by_user_id: mockRegularUser.id,
      updated_by_user_id: mockRegularUser.id,
      created_at: '2026-09-10T12:00:00Z',
      updated_at: '2026-09-10T12:00:00Z',
    });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /nuevo tipo/i })));

    expect(screen.getByRole('heading', { name: /nuevo tipo de análisis/i })).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/nombre del tipo de análisis/i), 'Análisis de Cárteles');
    await userEvent.type(screen.getByLabelText(/descripción breve/i), 'Detección y examen de indicios de colusión.');
    await userEvent.type(
      screen.getByLabelText(/instrucciones especializadas del modelo/i),
      'Instrucciones especializadas sobre cárteles e infracciones del art. 101 TFUE.'
    );

    fireEvent.click(screen.getByRole('button', { name: /^crear tipo de análisis/i }));

    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith({
        name: 'Análisis de Cárteles',
        description: 'Detección y examen de indicios de colusión.',
        instructions: 'Instrucciones especializadas sobre cárteles e infracciones del art. 101 TFUE.',
        is_active: true,
      });
      expect(screen.getByText(/creado correctamente/i)).toBeInTheDocument();
    });
  });

  it('7. Valida longitud mínima de nombre e instrucciones al crear tipo', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /nuevo tipo/i })));

    await userEvent.type(screen.getByLabelText(/nombre del tipo de análisis/i), 'A');
    await userEvent.type(screen.getByLabelText(/instrucciones especializadas del modelo/i), 'Corta');

    fireEvent.click(screen.getByRole('button', { name: /^crear tipo de análisis/i }));

    await waitFor(() => {
      expect(screen.getByText(/el nombre debe tener entre 2 y 150 caracteres/i)).toBeInTheDocument();
    });
  });

  it('8. Edita tipo de análisis existente mostrando código inmutable', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const updateSpy = vi.spyOn(analysisTypesApi, 'updateAnalysisType').mockResolvedValue({
      ...mockAnalysisTypes[0],
      name: 'Resumen ejecutivo modificado',
    });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByLabelText(`Editar ${mockAnalysisTypes[0].name}`)));

    expect(screen.getByRole('heading', { name: /editar tipo de análisis/i })).toBeInTheDocument();
    // Código identificador se visualiza como inmutable
    expect(screen.getAllByText('executive-summary').length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/inmutable \(preserva referencias de ejecución\)/i)).toBeInTheDocument();


    const nameInput = screen.getByLabelText(/^nombre/i);
    await userEvent.clear(nameInput);
    await userEvent.type(nameInput, 'Resumen ejecutivo modificado');

    fireEvent.click(screen.getByRole('button', { name: /guardar cambios/i }));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(
        mockAnalysisTypes[0].id,
        expect.objectContaining({
          name: 'Resumen ejecutivo modificado',
        })
      );
      expect(screen.getByText(/actualizado correctamente/i)).toBeInTheDocument();
    });
  });

  it('9. Permite activar o desactivar un tipo de análisis', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const updateSpy = vi.spyOn(analysisTypesApi, 'updateAnalysisType').mockResolvedValue({
      ...mockAnalysisTypes[0],
      is_active: false,
    });

    render(<App />);

    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => fireEvent.click(screen.getByLabelText(`Desactivar ${mockAnalysisTypes[0].name}`)));

    await waitFor(() => {
      expect(updateSpy).toHaveBeenCalledWith(mockAnalysisTypes[0].id, {
        is_active: false,
      });
      expect(screen.getByText(/desactivado correctamente/i)).toBeInTheDocument();
    });
  });

  // ─────────────────────────────────────────────
  // Tests de ELIMINACIÓN FÍSICA (Bloque 7C.1)
  // ─────────────────────────────────────────────

  it('10. Botón Eliminar visible para admin', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`)).toBeInTheDocument();
    });
  });

  it('11. Botón Eliminar visible también para user normal', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => {
      expect(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`)).toBeInTheDocument();
    });
  });

  it('12. Pulsar Eliminar NO borra inmediatamente — aparece modal de confirmación', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const deleteSpy = vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockResolvedValue();
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /eliminar tipo de análisis/i })).toBeInTheDocument();
    });
    expect(deleteSpy).not.toHaveBeenCalled();
  });

  it('13. Cancelar en modal de confirmación NO llama DELETE', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const deleteSpy = vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockResolvedValue();
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    fireEvent.click(screen.getByRole('button', { name: /^cancelar$/i }));
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /eliminar tipo de análisis/i })).not.toBeInTheDocument();
    });
    expect(deleteSpy).not.toHaveBeenCalled();
  });

  it('14. Confirmar eliminación llama DELETE y tipo desaparece del listado', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    const deleteSpy = vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockResolvedValue();
    vi.spyOn(analysisTypesApi, 'listAnalysisTypes')
      .mockResolvedValueOnce({ items: mockAnalysisTypes, total: 2 })
      .mockResolvedValue({ items: [mockAnalysisTypes[1]], total: 1 });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    fireEvent.click(screen.getByRole('button', { name: /eliminar definitivamente/i }));
    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledWith(mockAnalysisTypes[0].id);
      expect(screen.getByText(/eliminado definitivamente/i)).toBeInTheDocument();
    });
  });

  it('15. onTypesUpdated se llama tras eliminar exitosamente', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockResolvedValue();
    vi.spyOn(analysisTypesApi, 'listAnalysisTypes')
      .mockResolvedValueOnce({ items: mockAnalysisTypes, total: 2 })
      .mockResolvedValue({ items: [mockAnalysisTypes[1]], total: 1 });
    const onTypesUpdated = vi.fn();

    const { AuthProvider } = await import('../context/AuthContext');
    const { AnalysisTypesManagement } = await import('../components/AnalysisTypesManagement');

    render(
      <AuthProvider>
        <AnalysisTypesManagement onTypesUpdated={onTypesUpdated} />
      </AuthProvider>
    );

    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    fireEvent.click(screen.getByRole('button', { name: /eliminar definitivamente/i }));

    await waitFor(() => {
      expect(onTypesUpdated).toHaveBeenCalled();
    });
  });

  it('16. Fallo en DELETE mantiene el modal y muestra error — tipo permanece en listado', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockRejectedValue(new Error('Error de red al eliminar'));
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    fireEvent.click(screen.getByRole('button', { name: /eliminar definitivamente/i }));
    await waitFor(() => {
      expect(screen.getByText(/error de red al eliminar/i)).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /eliminar tipo de análisis/i })).toBeInTheDocument();
    });
  });

  it('17. Modal de eliminación muestra el nombre del tipo correctamente', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[1].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[1].name}`));
    await waitFor(() => {
      // El nombre aparece en el modal en un <strong> dentro del modal-body
      expect(screen.getByText(/no podrá recuperarse automáticamente/i)).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /eliminar tipo de análisis/i })).toBeInTheDocument();
    });
  });

  it('18. Botón destructivo está diferenciado visualmente del botón Cancelar', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => {
      const destructiveBtn = screen.getByRole('button', { name: /eliminar definitivamente/i });
      const cancelBtn = screen.getByRole('button', { name: /^cancelar$/i });
      expect(destructiveBtn).toHaveClass('btn-danger');
      expect(cancelBtn).toHaveClass('btn-secondary');
    });
  });

  it('19. Doble click en confirmar no envía dos peticiones DELETE', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockRegularUser, csrf_token: 'valid-csrf' });
    let resolveDelete!: () => void;
    const deletePromise = new Promise<void>((res) => { resolveDelete = res; });
    const deleteSpy = vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockReturnValue(deletePromise);
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    const confirmBtn = screen.getByRole('button', { name: /eliminar definitivamente/i });
    fireEvent.click(confirmBtn);
    fireEvent.click(confirmBtn); // segundo click — debe ser ignorado
    resolveDelete();
    await waitFor(() => {
      expect(deleteSpy).toHaveBeenCalledTimes(1);
    });
  });

  it('20. Tras eliminar, listado actualizado no muestra el tipo eliminado', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({ ...mockAdminUser, csrf_token: 'valid-csrf' });
    vi.spyOn(analysisTypesApi, 'deleteAnalysisType').mockResolvedValue();
    vi.spyOn(analysisTypesApi, 'listAnalysisTypes')
      .mockResolvedValueOnce({ items: mockAnalysisTypes, total: 2 })
      .mockResolvedValue({ items: [mockAnalysisTypes[1]], total: 1 });
    render(<App />);
    await waitFor(() => fireEvent.click(screen.getByRole('button', { name: /configuración/i })));
    await waitFor(() => screen.getByText(mockAnalysisTypes[0].name));
    await waitFor(() => screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    fireEvent.click(screen.getByLabelText(`Eliminar ${mockAnalysisTypes[0].name}`));
    await waitFor(() => screen.getByRole('heading', { name: /eliminar tipo de análisis/i }));
    fireEvent.click(screen.getByRole('button', { name: /eliminar definitivamente/i }));
    await waitFor(() => {
      expect(screen.queryByText(mockAnalysisTypes[0].name)).not.toBeInTheDocument();
    });
  });
});
