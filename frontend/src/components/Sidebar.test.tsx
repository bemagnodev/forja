import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Sidebar } from './Sidebar';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('Sidebar', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.mocked(api.get).mockResolvedValue({
      data: {
        first_name: 'Bê',
        last_name: 'Magno',
        username: 'bemagno',
      },
    } as never);
  });

  test('renderiza os botões de navegação e sincronização', async () => {
    await act(async () => {
      render(
        <MemoryRouter>
          <Sidebar />
        </MemoryRouter>
      );
    });

    expect(screen.getByText('Sincronizar CF')).toBeInTheDocument();
    expect(screen.getByText('Sincronizar AtCoder')).toBeInTheDocument();
  });

  test('exibe mensagem transparente de sincronização iniciada e não conclusão imediata ao disparar sync CF', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        success: true,
        message: 'Sincronização iniciada. Os dados serão atualizados em instantes.',
        handle: 'bemagno',
        changes: 0,
      },
    } as never);

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    const syncButton = screen.getByRole('button', { name: /Sincronizar CF/i });
    await user.click(syncButton);

    expect(api.post).toHaveBeenCalledWith('/sync/cf');
    expect(
      await screen.findByText('Sincronização iniciada. Os dados serão atualizados em instantes.')
    ).toBeInTheDocument();
    expect(screen.queryByText('Concluído!')).not.toBeInTheDocument();
  });

  test('exibe mensagem de erro quando a API de sincronização falhar', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        success: false,
        message: 'Nenhum handle configurado.',
      },
    } as never);

    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>
    );

    const syncButton = screen.getByRole('button', { name: /Sincronizar CF/i });
    await user.click(syncButton);

    expect(api.post).toHaveBeenCalledWith('/sync/cf');
    expect(await screen.findByText('Nenhum handle configurado.')).toBeInTheDocument();
  });
});
