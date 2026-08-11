import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PromptSettings } from '../src/components/PromptSettings';
import * as promptService from '../src/services/prompts';
import React from 'react';
import { TipoPrompt, ModeloOpenAI, TipoFerramenta } from '../src/services/api';

// Mock the hook
vi.mock('../src/services/prompts', () => ({
  usePrompts: vi.fn()
}));

describe('PromptSettings Component', () => {
  const mockAddPrompt = vi.fn();
  const mockFetchDefaultPromptText = vi.fn().mockResolvedValue('Default instructions here');
  const mockDeletePrompt = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (promptService.usePrompts as any).mockImplementation((tool: TipoFerramenta) => {
      let prompts = [];
      if (tool === 'extrator') {
        prompts = [
          { 
            id: '00000000-0000-0000-0000-000000000001', 
            nome: 'Extrator Padrão', 
            tipo: 'FIXO' as TipoPrompt,
            textoInstrucao: 'Extraia tudo.',
            palavrasChave: [],
            idiomaModelo: 'pt-br',
            modeloOpenAI: 'gpt-4o-mini' as ModeloOpenAI,
            ferramenta: 'extrator' as TipoFerramenta
          }
        ];
      } else if (tool === 'gerador') {
        prompts = [
          { 
            id: '00000000-0000-0000-0000-000000000002', 
            nome: 'Gerador Padrão', 
            tipo: 'FIXO' as TipoPrompt,
            textoInstrucao: 'Gere tudo.',
            palavrasChave: [],
            idiomaModelo: 'pt-br',
            modeloOpenAI: 'gpt-4o-mini' as ModeloOpenAI,
            ferramenta: 'gerador' as TipoFerramenta
          }
        ];
      } else if (tool === 'consolidador') {
        prompts = [
          { 
            id: '00000000-0000-0000-0000-000000000003', 
            nome: 'Consolidador Padrão', 
            tipo: 'FIXO' as TipoPrompt,
            textoInstrucao: 'Consolide tudo.',
            palavrasChave: [],
            idiomaModelo: 'pt-br',
            modeloOpenAI: 'gpt-4o-mini' as ModeloOpenAI,
            ferramenta: 'consolidador' as TipoFerramenta
          }
        ];
      }
      return {
        prompts,
        loading: false,
        error: null,
        addPrompt: mockAddPrompt,
        deletePrompt: mockDeletePrompt,
        fetchDefaultPromptText: mockFetchDefaultPromptText,
      }
    });
  });

  it('renders correctly with default tool (extrator) and scoped prompts', () => {
    render(<PromptSettings />);
    expect(screen.getByText('Configurações de Prompt')).toBeDefined();
    expect(screen.getByText('Extrator Padrão')).toBeDefined();
    expect(screen.queryByText('Gerador Padrão')).toBeNull();
  });

  it('switches tool tabs and loads scoped prompts', () => {
    render(<PromptSettings />);
    
    // Switch to gerador
    fireEvent.click(screen.getByText('Gerador'));
    expect(promptService.usePrompts).toHaveBeenCalledWith('gerador');
    expect(screen.getByText('Gerador Padrão')).toBeDefined();
    expect(screen.queryByText('Extrator Padrão')).toBeNull();
  });

  it('handles adding a new prompt with correct tool binding', async () => {
    render(<PromptSettings />); // extrator is default
    
    const nameInput = screen.getByPlaceholderText(/Ex: Extrator Inglês Detalhado/i);
    const instructionInput = screen.getByPlaceholderText(/Instruções para o LLM/i);
    const keywordsInput = screen.getByPlaceholderText(/Ex: dúvidas, faq, suporte/i);
    const langInput = screen.getByPlaceholderText(/Ex: pt-br, en-us/i);
    const addButton = screen.getByRole('button', { name: /Salvar Prompt/i });

    fireEvent.change(nameInput, { target: { value: 'New Prompt' } });
    fireEvent.change(instructionInput, { target: { value: 'This is a long enough instruction.' } });
    fireEvent.change(keywordsInput, { target: { value: 'foo, bar' } });
    fireEvent.change(langInput, { target: { value: 'en-us' } });
    
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(mockAddPrompt).toHaveBeenCalledWith({
        nome: 'New Prompt',
        textoInstrucao: 'This is a long enough instruction.',
        palavrasChave: ['foo', 'bar'],
        idiomaModelo: 'en-us',
        modeloOpenAI: 'gpt-4o-mini',
        ferramenta: 'extrator' // Bound to the active tool
      });
    });
  });

  it('handles default prompt duplication with correct naming', async () => {
    render(<PromptSettings />);
    
    // Extrator is selected. Click duplicate.
    const duplicateButton = screen.getByTitle('Duplicar "Extrator Padrão" como customizado');
    fireEvent.click(duplicateButton);

    await waitFor(() => {
      expect(mockFetchDefaultPromptText).toHaveBeenCalled();
    });

    // Check if the form is pre-filled with "<Nome Padrão> (Cópia)"
    const nameInput = screen.getByDisplayValue('Extrator Padrão (Cópia)');
    expect(nameInput).toBeDefined();

    const instructionInput = screen.getByDisplayValue('Default instructions here');
    expect(instructionInput).toBeDefined();
  });

  it('shows error state correctly', () => {
    (promptService.usePrompts as any).mockReturnValue({
      prompts: [],
      loading: false,
      error: 'Error saving prompt',
      addPrompt: mockAddPrompt,
      deletePrompt: mockDeletePrompt,
      fetchDefaultPromptText: mockFetchDefaultPromptText
    });

    render(<PromptSettings />);
    expect(screen.getByText('Error saving prompt')).toBeDefined();
  });
});
