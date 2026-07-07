import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KeySettings } from '../src/components/KeySettings';
import * as keyService from '../src/services/keys';
import React from 'react';

// Mock the hook
vi.mock('../src/services/keys', () => ({
  useKeys: vi.fn()
}));

describe('KeySettings Component', () => {
  const mockAddKey = vi.fn();
  const mockRemoveKey = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    (keyService.useKeys as any).mockReturnValue({
      keys: [
        { id: '1', nomeIdentificacao: 'Test Key', chave: 'sk-123456789' }
      ],
      loading: false,
      error: null,
      addKey: mockAddKey,
      removeKey: mockRemoveKey
    });
  });

  it('renders correctly with existing keys', () => {
    render(<KeySettings />);
    expect(screen.getByText('Chaves de API')).toBeDefined();
    expect(screen.getByText('Test Key')).toBeDefined();
    expect(screen.getByText(/sk-1...6789/)).toBeDefined();
  });

  it('handles adding a new key', async () => {
    render(<KeySettings />);
    
    const nameInput = screen.getByPlaceholderText('Ex: Minha Chave Principal');
    const keyInput = screen.getByPlaceholderText('sk-...');
    const addButton = screen.getByRole('button', { name: /Adicionar/i });

    fireEvent.change(nameInput, { target: { value: 'New Key' } });
    fireEvent.change(keyInput, { target: { value: 'sk-new123' } });
    
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(mockAddKey).toHaveBeenCalledWith({
        nomeIdentificacao: 'New Key',
        chave: 'sk-new123'
      });
    });
  });

  it('handles deleting a key', async () => {
    render(<KeySettings />);
    
    const deleteButton = screen.getByTitle('Remover Chave');
    fireEvent.click(deleteButton);

    await waitFor(() => {
      expect(mockRemoveKey).toHaveBeenCalledWith('1');
    });
  });

  it('shows error state correctly', () => {
    (keyService.useKeys as any).mockReturnValue({
      keys: [],
      loading: false,
      error: 'Error message here',
      addKey: mockAddKey,
      removeKey: mockRemoveKey
    });

    render(<KeySettings />);
    expect(screen.getByText('Error message here')).toBeDefined();
  });
});
