import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { Sidebar } from './Sidebar';
import { api } from '@/lib/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
function renderSidebar() {
  return render(<QueryClientProvider client={queryClient}><MemoryRouter><Sidebar /></MemoryRouter></QueryClientProvider>);
}

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe('Sidebar', () => {
  beforeEach(() => {
    vi.useRealTimers();
    localStorage.clear();
    vi.restoreAllMocks();
    vi.clearAllMocks();
    queryClient.clear();
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
      renderSidebar();
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
        state: 'running',
        run_id: 'run-one',
      },
    } as never);

    vi.mocked(api.get).mockImplementation(async (url) => url === '/sync/cf/status'
      ? { data: { state: 'running', message: 'Aguarde.' } } as never
      : { data: { username: 'bemagno' } } as never);
    renderSidebar();

    const syncButton = screen.getByRole('button', { name: /Sincronizar CF/i });
    await user.click(syncButton);

    expect(api.post).toHaveBeenCalledWith('/sync/cf');
    expect(
      await screen.findByText('Sincronização iniciada. Os dados serão atualizados em instantes.')
    ).toBeInTheDocument();
    expect(screen.queryByText('Concluído!')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sincronizando/i })).toBeDisabled();
  });

  test('exibe mensagem de erro quando a API de sincronização falhar', async () => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValueOnce({
      data: {
        success: false,
        message: 'Nenhum handle configurado.',
      },
    } as never);

    renderSidebar();

    const syncButton = screen.getByRole('button', { name: /Sincronizar CF/i });
    await user.click(syncButton);

    expect(api.post).toHaveBeenCalledWith('/sync/cf');
    expect(await screen.findByText('Nenhum handle configurado.')).toBeInTheDocument();
  });

  test.each(['completed', 'failed', 'interrupted', 'unknown'])('acompanha o estado real %s e só atualiza dados após conclusão', async (state) => {
    const user = userEvent.setup();
    vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true, state: 'running', run_id: 'r', message: 'Iniciada.' } } as never);
    vi.mocked(api.get).mockImplementation(async (url) => url === '/sync/cf/status'
      ? { data: { state, message: `Estado final ${state}` } } as never
      : { data: { username: 'bemagno' } } as never);
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries');
    const notify = vi.fn();
    window.addEventListener('forja:cf-sync-completed', notify);
    try {
      renderSidebar();
      await user.click(screen.getByRole('button', { name: /Sincronizar CF/i }));
      expect(await screen.findByText(`Estado final ${state}`)).toBeVisible();
      expect(api.get).toHaveBeenCalledWith('/sync/cf/status', { params: { run_id: 'r' } });
      if (state === 'completed') {
        await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['contests'] }));
        expect(invalidate).toHaveBeenCalledWith({ queryKey: ['queue'] });
        expect(invalidate).toHaveBeenCalledWith({ queryKey: ['contest-problems'] });
        expect(notify).toHaveBeenCalledOnce();
      } else {
        expect(invalidate).not.toHaveBeenCalled();
        expect(notify).not.toHaveBeenCalled();
      }
    } finally {
      window.removeEventListener('forja:cf-sync-completed', notify);
    }
  });

  test('consulta novamente sem redisparar o sync e cancela polling ao desmontar', async () => {
    const user = userEvent.setup();
    let releaseFirstPoll: (value: unknown) => void = () => { throw new Error('poll not started'); };
    const firstPoll = new Promise(resolve => { releaseFirstPoll = resolve; });
    let statusCalls = 0;
    vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true, state: 'running', run_id: 'r', message: 'Iniciada.' } } as never);
    vi.mocked(api.get).mockImplementation(async (url) => {
      if (url !== '/sync/cf/status') return { data: { username: 'bemagno' } } as never;
      statusCalls += 1;
      if (statusCalls === 1) return firstPoll as never;
      return { data: { state: 'running', message: 'Aguarde.' } } as never;
    });
    const view = renderSidebar();
    try {
      await user.click(screen.getByRole('button', { name: /Sincronizar CF/i }));
      await user.click(screen.getByRole('button', { name: /Sincronizando/i }));
      expect(api.post).toHaveBeenCalledTimes(1);
      vi.useFakeTimers();
      await act(async () => { releaseFirstPoll({ data: { state: 'running', message: 'Aguarde.' } }); });
      await act(async () => { await vi.advanceTimersByTimeAsync(3000); });
      expect(vi.mocked(api.get).mock.calls.filter(([url]) => url === '/sync/cf/status')).toHaveLength(2);
      view.unmount();
      await act(async () => { await vi.advanceTimersByTimeAsync(6000); });
      expect(vi.mocked(api.get).mock.calls.filter(([url]) => url === '/sync/cf/status')).toHaveLength(2);
    } finally {
      view.unmount();
      vi.useRealTimers();
    }
  });

  test('falha ao consultar estado não repete a sincronização nem anuncia sucesso', async () => {
    vi.mocked(api.post).mockResolvedValueOnce({ data: { success: true, state: 'running', run_id: 'r', message: 'Iniciada.' } } as never);
    vi.mocked(api.get).mockImplementation(async (url) => {
      if (url === '/sync/cf/status') throw new Error('signed-url-or-secret');
      return { data: { username: 'bemagno' } } as never;
    });
    renderSidebar();
    await userEvent.setup().click(screen.getByRole('button', { name: /Sincronizar CF/i }));
    expect(await screen.findByText(/Não foi possível acompanhar/)).toBeVisible();
    expect(api.post).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/signed-url-or-secret/)).not.toBeInTheDocument();
  });
});
