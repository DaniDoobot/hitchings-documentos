import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '../App';
import * as authApi from '../api/auth';
import * as promptsApi from '../api/prompts';
import * as analysisTypesApi from '../api/analysisTypes';
import * as promptSettingsApi from '../api/promptSettings';
import * as usersApi from '../api/users';
import type { UserPublic } from '../types/auth';
import type { AnalysisType } from '../types/analysisTypes';
import type {
  PromptSetting,
  EffectiveInstructionsResponse,
  PromptOptionsGuidelines,
} from '../types/promptSettings';

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

const mockBasePrompt: PromptSetting = {
  id: '33333333-3333-3333-3333-333333333333',
  key: 'analysis_base_prompt',
  content: 'Eres un asistente jurídico de élite para el despacho Hitchings y Gonzalez...',
  created_at: '2026-09-08T10:00:00Z',
  updated_at: '2026-09-10T15:30:00Z',
  updated_by_user_id: '11111111-1111-1111-1111-111111111111',
  updated_by_email: 'admin@hitchings-gonzalez.com',
};

const mockAnalysisTypes: AnalysisType[] = [
  {
    id: 'a1000000-0000-0000-0000-000000000001',
    code: 'legal-analysis',
    name: 'Análisis jurídico',
    description: 'Examen de partes, pretensiones y fundamentos de derecho.',
    instructions: 'Instrucciones específicas del tipo de análisis jurídico...',
    is_active: true,
    created_by_user_id: null,
    updated_by_user_id: null,
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
  },
];

const mockEffectiveInstructions: EffectiveInstructionsResponse = {
  base_prompt: 'Eres un asistente jurídico de élite para el despacho Hitchings y Gonzalez...',
  type_name: 'Análisis jurídico',
  type_instructions: 'Instrucciones específicas del tipo de análisis jurídico...',
  detail_level: 'standard',
  detail_modifier: 'Proporciona un análisis equilibrado con nivel de detalle estándar.',
  output_format: 'sections',
  format_modifier: 'Estructura la respuesta mediante secciones temáticas claras.',
  additional_instructions: 'Prestar especial atención a la cláusula penal.',
  effective_full_prompt:
    'Eres un asistente jurídico de élite para el despacho Hitchings y Gonzalez...\n\n---\n\nInstrucciones específicas del tipo de análisis jurídico...\n\n---\n\nProporciona un análisis equilibrado con nivel de detalle estándar.\n\n---\n\nEstructura la respuesta mediante secciones temáticas claras.\n\n---\n\nINSTRUCCIONES ADICIONALES DEL USUARIO:\nPrestar especial atención a la cláusula penal.',
};

const mockGuidelines: PromptOptionsGuidelines = {
  detail_levels: {
    concise: 'Sé conciso.',
    standard: 'Proporciona un análisis equilibrado con nivel de detalle estándar.',
    detailed: 'Sé exhaustivo.',
  },
  output_formats: {
    executive: 'Formato ejecutivo.',
    sections: 'Estructura la respuesta mediante secciones temáticas claras.',
    bullet_points: 'Puntos clave.',
  },
};

describe('Bloque 7D — Flexibilidad Total de Prompts y Transparencia', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(authApi, 'getMe').mockResolvedValue({
      ...mockAdminUser,
      csrf_token: 'test-csrf-token-12345',
    });
    vi.spyOn(promptsApi, 'fetchPrompts').mockResolvedValue(
      mockAnalysisTypes.map((t) => ({
        id: t.code,
        name: t.name,
        description: t.description,
        instructions: t.instructions,
        is_active: t.is_active,
        is_system: false,
        created_at: t.created_at,
        updated_at: t.updated_at,
      }))
    );
    vi.spyOn(analysisTypesApi, 'listAnalysisTypes').mockResolvedValue({
      items: mockAnalysisTypes,
      total: 1,
    });
    vi.spyOn(promptSettingsApi, 'getBasePrompt').mockResolvedValue(mockBasePrompt);
    vi.spyOn(promptSettingsApi, 'updateBasePrompt').mockImplementation(async (content) => ({
      ...mockBasePrompt,
      content,
      updated_at: new Date().toISOString(),
      updated_by_email: 'admin@hitchings-gonzalez.com',
    }));
    vi.spyOn(promptSettingsApi, 'getOptionsGuidelines').mockResolvedValue(mockGuidelines);
    vi.spyOn(promptSettingsApi, 'previewEffectiveInstructions').mockResolvedValue(
      mockEffectiveInstructions
    );
    vi.spyOn(usersApi, 'listUsers').mockResolvedValue({
      users: [mockAdminUser],
      total: 1,
    });
  });

  it('permite a un usuario administrador ver y navegar a la pestaña "Prompt base"', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /prompt base/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /usuarios/i })).toBeInTheDocument();
    });
  });

  it('permite a un usuario normal (rol user) ver la pestaña "Prompt base" y "Tipos de análisis", pero no "Usuarios"', async () => {
    vi.spyOn(authApi, 'getMe').mockResolvedValue({
      ...mockRegularUser,
      csrf_token: 'test-csrf-token-regular',
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /prompt base/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
      expect(screen.queryByRole('tab', { name: /usuarios/i })).not.toBeInTheDocument();
    });
  });

  it('muestra el contenido del Prompt Base y permite editarlo y guardarlo', async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /prompt base/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /prompt base/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/contenido sustantivo del prompt base/i)).toBeInTheDocument();
    });

    const textarea = screen.getByLabelText(/contenido sustantivo del prompt base/i);
    expect(textarea).toHaveValue(mockBasePrompt.content);

    // Escribir nuevo contenido
    await user.clear(textarea);
    await user.type(textarea, 'Nuevo marco jurídico general del despacho actualizado.');

    const saveBtn = screen.getByRole('button', { name: /guardar cambios/i });
    expect(saveBtn).not.toBeDisabled();

    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(promptSettingsApi.updateBasePrompt).toHaveBeenCalledWith(
        'Nuevo marco jurídico general del despacho actualizado.'
      );
      expect(
        screen.getByText(/prompt base global guardado correctamente/i)
      ).toBeInTheDocument();
    });
  });

  it('permite desplegar la "Vista previa del prompt completo" en la edición de un tipo de análisis', async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /configuración/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /configuración/i }));

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: /tipos de análisis/i })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: /tipos de análisis/i }));

    await waitFor(() => {
      expect(screen.getByText('Análisis jurídico')).toBeInTheDocument();
    });

    const editBtn = screen.getByLabelText(`Editar ${mockAnalysisTypes[0].name}`);
    fireEvent.click(editBtn);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /editar tipo de análisis/i })).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /vista previa del prompt completo/i })
      ).toBeInTheDocument();
    });

    const togglePreviewBtn = screen.getByRole('button', {
      name: /vista previa del prompt completo/i,
    });
    fireEvent.click(togglePreviewBtn);

    await waitFor(() => {
      expect(screen.getByText('PROMPT BASE GLOBAL')).toBeInTheDocument();
      expect(screen.getByText(/PROMPT DEL TIPO:/i)).toBeInTheDocument();
      expect(
        screen.getByText('Eres un asistente jurídico de élite para el despacho Hitchings y Gonzalez...')
      ).toBeInTheDocument();
    });
  });

  it('abre el modal "Ver instrucciones utilizadas" en la pantalla de análisis con las 5 capas desglosadas', async () => {
    render(<App />);

    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /ver instrucciones utilizadas/i });
      expect(btn).toBeInTheDocument();
      expect(btn).not.toBeDisabled();
    });

    const viewInstructionsBtn = screen.getByRole('button', {
      name: /ver instrucciones utilizadas/i,
    });
    fireEvent.click(viewInstructionsBtn);

    await waitFor(() => {
      expect(
        screen.getByRole('dialog', { name: /instrucciones utilizadas para el análisis/i })
      ).toBeInTheDocument();
    });

    // Verificar las 5 capas requeridas
    await waitFor(() => {
      expect(screen.getByText('Prompt Base Global del Despacho')).toBeInTheDocument();
      expect(screen.getByText(/Tipo de Análisis:/)).toBeInTheDocument();
      expect(screen.getByText(/Modificador de Nivel de Detalle:/)).toBeInTheDocument();
      expect(screen.getByText(/Modificador de Formato de Salida:/)).toBeInTheDocument();
      expect(screen.getByText('Instrucciones Adicionales del Usuario')).toBeInTheDocument();
    });

    // Comprobar cambio a vista integrada
    const integratedTab = screen.getByRole('button', { name: /prompt completo integrado/i });
    fireEvent.click(integratedTab);

    await waitFor(() => {
      expect(
        screen.getByText(/esta es la composición completa de directivas intelectuales/i)
      ).toBeInTheDocument();
    });

    // Cerrar modal con botón Cerrar exacto
    const closeBtn = screen.getByRole('button', { name: /^cerrar$/i });
    fireEvent.click(closeBtn);

    await waitFor(() => {
      expect(
        screen.queryByRole('dialog', { name: /instrucciones utilizadas para el análisis/i })
      ).not.toBeInTheDocument();
    });
  });
});
