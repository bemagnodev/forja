import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContestDetail } from './ContestDetail';
const mocks = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), toast: vi.fn() }));
vi.mock('@/lib/api', () => ({ api: mocks }));
vi.mock('@/components/ui/toast-context', () => ({ useToast: () => ({ toast: mocks.toast }) }));
const detail = { contest_name: 'Treino atualizado', url: 'https://codeforces.com/gym/106687', rank: 3, progress: { solved_live: 0, upsolved: 0, pending_upsolve: 0, unattempted: 1, total: 1 } };
const problem = { id: 7, title: 'Problema F', platform_id: '106687F', index: 'F', tags: [], rating: 1400, system_status: 'UNATTEMPTED', review_status: 'PENDING_TRIAGE' };
beforeEach(() => { vi.clearAllMocks(); mocks.get.mockImplementation(async (url: string) => ({ data: url.endsWith('/problems') ? [problem] : detail })); });
function mount(state?: object) { const client = new QueryClient({ defaultOptions: { queries: { retry: false } } }); render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[{ pathname: '/contests/42', state }]}><Routes><Route path='/contests/:id' element={<ContestDetail />} /></Routes></MemoryRouter></QueryClientProvider>); return client; }
it('carrega nome e link pelo ID ao entrar diretamente sem state', async () => {
  mount(); expect(await screen.findByText(detail.contest_name)).toBeVisible();
  expect(screen.getByTitle('Abrir contest na plataforma')).toHaveAttribute('href', detail.url);
});
it('substitui metadados antigos da navegação pela resposta atual', async () => {
  mount({ contest_name: 'Nome antigo', progress: { total: 99 } });
  expect(await screen.findByText(detail.contest_name)).toBeVisible(); expect(screen.queryByText('Nome antigo')).toBeNull();
});
it('mostra erro recuperável para detalhe inexistente sem usar state como sucesso', async () => {
  mocks.get.mockRejectedValue(new Error('404')); mount({ contest_name: 'Nome antigo' });
  expect(await screen.findByText(/Não foi possível carregar/)).toBeVisible();
});
it('alterar revisão invalida os resumos e mantém status anterior no erro', async () => {
  mocks.patch.mockRejectedValue(new Error('500')); const client = mount(); const spy = vi.spyOn(client, 'invalidateQueries');
  await screen.findByText('Problema F'); await userEvent.click(screen.getByRole('button', { name: 'Pendente' }));
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Concluído' }));
  await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' })));
  expect(screen.getByRole('button', { name: 'Pendente' })).toBeVisible(); expect(spy).not.toHaveBeenCalled();
  mocks.patch.mockResolvedValue({ data: {} }); await userEvent.click(screen.getByRole('button', { name: 'Pendente' }));
  await userEvent.click(await screen.findByRole('menuitem', { name: 'Concluído' }));
  await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['contest', 42] }));
  for (const key of ['dashboard', 'queue', 'contests']) expect(spy).toHaveBeenCalledWith({ queryKey: [key] });
});
