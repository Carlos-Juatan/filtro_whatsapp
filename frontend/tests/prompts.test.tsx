import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { PromptSettings } from '../src/components/PromptSettings';
import * as promptService from '../src/services/prompts';
import React from 'react';
import { TipoPrompt, ModeloOpenAI } from '../src/services/api';

// Mock the hook
vi.mock('../src/services/prompts', () => ({
  usePrompts: vi.fn()
}));

describe('PromptSettings Component', () => {
  const mockAddPrompt = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (promptService.usePrompts as any).mockReturnValue({
      prompts: [
        { 
          id: '1', 
          nome: 'Extrator Especial', 
          tipo: 'CUSTOMIZADO' as TipoPrompt,
          textoInstrucao: 'Extraia tudo.',
          palavrasChave: ['teste', 'vitest'],
          idiomaModelo: 'pt-br',
          modeloOpenAI: 'gpt-4o' as ModeloOpenAI
        }
      ],
      loading: false,
      error: null,
      addPrompt: mockAddPrompt
    });
  });

  it('renders correctly with existing prompts', () => {
    render(<PromptSettings />);
    expect(screen.getByText('Configurações de Prompt')).toBeDefined();
    expect(screen.getByText('Extrator Especial')).toBeDefined();
    expect(screen.getByText('CUSTOMIZADO')).toBeDefined();
  });

  it('handles adding a new prompt', async () => {
    render(<PromptSettings />);
    
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
        modeloOpenAI: 'gpt-4o-mini' // Default in component state
      });
    });
  });

  it('shows error state correctly', () => {
    (promptService.usePrompts as any).mockReturnValue({
      prompts: [],
      loading: false,
      error: 'Error saving prompt',
      addPrompt: mockAddPrompt
    });

    render(<PromptSettings />);
    expect(screen.getByText('Error saving prompt')).toBeDefined();
  });
});
