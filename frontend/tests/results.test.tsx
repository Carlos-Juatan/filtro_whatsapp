import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { expect, test, describe, vi } from 'vitest';
import { ResultsTable } from '../src/components/ResultsTable';
import { exportToJson, exportToTxt } from '../src/utils/export';
import { ResultadoParPR } from '../src/services/api';

describe('ResultsTable Component', () => {
  const mockResults: ResultadoParPR[] = [
    {
      perguntaPadronizada: 'Qual horário?',
      respostaConsolidada: 'Das 8h as 18h.',
      frequencia: 2,
      category: 'Atendimento'
    },
    {
      perguntaPadronizada: 'Como pagar?',
      respostaConsolidada: 'Cartão ou Pix.',
      frequencia: 5,
      category: 'Financeiro'
    }
  ];

  test('renders empty state when no results', () => {
    render(<ResultsTable results={[]} />);
    expect(screen.getByText(/Nenhum resultado processado/i)).toBeInTheDocument();
  });

  test('renders results and allows searching', () => {
    render(<ResultsTable results={mockResults} />);
    
    // Check initial render
    expect(screen.getByText('Qual horário?')).toBeInTheDocument();
    expect(screen.getByText('Como pagar?')).toBeInTheDocument();
    expect(screen.getByText('Atendimento')).toBeInTheDocument();
    expect(screen.getByText('Financeiro')).toBeInTheDocument();

    // Search for 'pagar'
    const searchInput = screen.getByPlaceholderText(/Buscar/i);
    fireEvent.change(searchInput, { target: { value: 'pagar' } });

    // Should show the second result, not the first
    expect(screen.getByText('Como pagar?')).toBeInTheDocument();
    expect(screen.queryByText('Qual horário?')).not.toBeInTheDocument();
  });
});

describe('Export Utilities', () => {
  const mockResults: ResultadoParPR[] = [
    {
      perguntaPadronizada: 'Test Q',
      respostaConsolidada: 'Test A',
      frequencia: 1,
      category: 'Cat'
    }
  ];

  test('exportToTxt calls createObjectURL', () => {
    const createObjectURL = vi.fn(() => 'blob:test');
    const revokeObjectURL = vi.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;
    
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    exportToTxt(mockResults);
    
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
    clickSpy.mockRestore();
  });

  test('exportToJson calls createObjectURL', () => {
    const createObjectURL = vi.fn(() => 'blob:test');
    const revokeObjectURL = vi.fn();
    window.URL.createObjectURL = createObjectURL;
    window.URL.revokeObjectURL = revokeObjectURL;
    
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

    exportToJson(mockResults);
    
    expect(createObjectURL).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalled();
    clickSpy.mockRestore();
  });
});
