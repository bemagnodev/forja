import { MemoryRouter, Route, Routes } from "react-router-dom";
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, it, vi } from 'vitest';
import { ProblemActionsCell } from './contests/ProblemActionsCell';
import { ToastProvider } from './ui/toast';
import { api } from '@/lib/api';
import { NATIVE_RATING_MESSAGE } from '@/lib/product-classification';
import { Queue } from '@/pages/Queue';
import { TooltipProvider } from './ui/tooltip';

vi.mock('@/lib/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it('exibe a restrição em toast vermelho no rodapé e não abaixo do classificador', async () => {
  const client = new QueryClient();
  const view = render(<QueryClientProvider client={client}><MemoryRouter><ToastProvider>
    <ProblemActionsCell problem={{ id: 7, platform_id: '7A', title: 'Test', index: 'A',
      rating: 1200, ai_rating: null, tags: [], ai_tags: [], url: null,
      system_status: 'UNATTEMPTED', review_status: 'PENDING_TRIAGE', tracking_id: null }} />
  </ToastProvider></MemoryRouter></QueryClientProvider>);
  await userEvent.setup().click(screen.getByRole('button', { name: 'Estimar rating e tags com IA' }));
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent(NATIVE_RATING_MESSAGE);
  expect(alert).toHaveClass('border-red-500/20');
  expect(alert.closest('.fixed')).toHaveClass('bottom-8');
  expect(screen.getByText(NATIVE_RATING_MESSAGE)).not.toHaveClass('truncate');
  expect(view.container.querySelectorAll('p[role="status"]')).toHaveLength(0);
  expect(api.post).not.toHaveBeenCalled();
});

it('abre a Fila pelo toast e destaca temporariamente apenas o item criado', async () => {
  const item = { title: 'Grafos', item_type: 'PROBLEM', priority: 'UPSOLVING', tags: [], is_completed: false };
  vi.mocked(api.post).mockResolvedValueOnce({ data: { id: 42 } });
  vi.mocked(api.get).mockResolvedValue({ data: [{ ...item, id: 41 }, { ...item, id: 42 }] });
  const client = new QueryClient();
  const user = userEvent.setup();
  render(<QueryClientProvider client={client}>
    <MemoryRouter initialEntries={['/contests/1']}>
      <ToastProvider><TooltipProvider><Routes>
        <Route path="/contests/1" element={<ProblemActionsCell problem={{
          id: 7, platform_id: '7A', title: 'Grafos', index: 'A', rating: null,
          ai_rating: null, tags: [], ai_tags: [], url: null, system_status: 'UNATTEMPTED',
          review_status: 'PENDING_TRIAGE', tracking_id: null,
        }} />} />
        <Route path="/" element={<Queue />} />
      </Routes></TooltipProvider></ToastProvider>
    </MemoryRouter>
  </QueryClientProvider>);
  await user.click(screen.getByRole('button', { name: 'Adicionar à Fila (Upsolving)' }));
  expect(await screen.findByText('Problema adicionado à fila')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Ver na fila' }));
  const rows = await screen.findAllByRole('row', { name: /Grafos/ });
  expect(rows[0]).not.toHaveAttribute('data-highlighted');
  expect(rows[1]).toHaveAttribute('data-highlighted', 'true');
  expect(rows[1]).toHaveFocus();
  await waitFor(() => expect(rows[1]).not.toHaveAttribute('data-highlighted'), { timeout: 4000 });
}, 8000);
