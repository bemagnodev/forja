import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Contests } from './Contests';

const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('@/lib/api', () => ({ api: mocks }));
const data = Array.from({ length: 12 }, (_, i) => ({ id: i + 1, contest_id: i + 1,
  contest_name: `Treino ${i + 1}`, contest_platform: i === 11 ? 'CF_OFFICIAL' : 'CF_GYM',
  participation_date: `2026-10-${String(25 - i).padStart(2, '0')}T12:00:00Z`, is_virtual: true,
  has_debt: false, progress: { solved_live: i + 1, upsolved: 1, total: 14, pending_upsolve: 0, unattempted: 12 - i },
  rank: null, url: null }));
beforeEach(() => {
  mocks.get.mockResolvedValue({ data });
  Object.defineProperty(window, 'matchMedia', { writable: true, value: vi.fn((query: string) => ({
    matches: query.includes('1280'), media: query, addEventListener: vi.fn(), removeEventListener: vi.fn(),
  })) });
  window.sessionStorage.clear();
});
function mount() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><Contests /></MemoryRouter></QueryClientProvider>);
}
it('pagina os cards mas mantém indicadores e evolução de todo o recorte', async () => {
  mount();
  const cards = await screen.findByRole('region', { name: 'Histórico de contests' });
  expect(within(cards).getAllByRole('link')).toHaveLength(9);
  expect(screen.getByRole('region', { name: 'Resultados por contest' })).toBeVisible();
  expect(screen.getByTestId('metric-contests')).toHaveTextContent('12');
  expect(screen.getByRole('button', { name: 'Equipe' })).toBeVisible();
  expect(screen.getByRole('button', { name: 'Individual' })).toBeVisible();
  expect(screen.getByText('Pendências')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Próxima página' }));
  expect(within(cards).getAllByRole('link')).toHaveLength(3);
  expect(screen.getByTestId('metric-contests')).toHaveTextContent('12');
});
it('mantém o resultado da barra visível após o clique ou toque', async () => {
  mount();
  const chart = await screen.findByRole('region', { name: 'Resultados por contest' });
  await userEvent.click(within(chart).getByRole('button', { name: /^Treino 1:/ }));
  expect(within(chart).getByRole('status')).toHaveTextContent('Treino 1');
});
it('filtra por plataforma e busca, restaurando os filtros ao voltar', async () => {
  const mounted = mount(); await screen.findByRole('region', { name: 'Histórico de contests' });
  await userEvent.click(screen.getByRole('button', { name: 'Individual' }));
  expect(within(screen.getByRole('region', { name: 'Histórico de contests' })).getAllByRole('link')).toHaveLength(1);
  await userEvent.type(screen.getByRole('searchbox', { name: 'Buscar contest' }), 'inexistente');
  expect(screen.getByText('Nenhum contest neste recorte')).toBeVisible();
  mounted.unmount(); mount();
  expect(await screen.findByRole('searchbox')).toHaveValue('inexistente');
});
