import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { afterEach, expect, it, vi } from 'vitest';
import { ProblemActionsCell } from './contests/ProblemActionsCell';
import { ToastProvider } from './ui/toast';
import { api } from '@/lib/api';
import { NATIVE_RATING_MESSAGE } from '@/lib/product-classification';

vi.mock('@/lib/api', () => ({ api: { post: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it('exibe a restrição em toast vermelho no rodapé e não abaixo do classificador', async () => {
  const client = new QueryClient();
  const view = render(<QueryClientProvider client={client}><ToastProvider>
    <ProblemActionsCell problem={{ id: 7, platform_id: '7A', title: 'Test', index: 'A',
      rating: 1200, ai_rating: null, tags: [], ai_tags: [], url: null,
      system_status: 'UNATTEMPTED', review_status: 'PENDING_TRIAGE', tracking_id: null }} />
  </ToastProvider></QueryClientProvider>);
  await userEvent.setup().click(screen.getByRole('button', { name: 'Estimar rating e tags com IA' }));
  const alert = await screen.findByRole('alert');
  expect(alert).toHaveTextContent(NATIVE_RATING_MESSAGE);
  expect(alert).toHaveClass('border-red-500/20');
  expect(alert.closest('.fixed')).toHaveClass('bottom-8');
  expect(screen.getByText(NATIVE_RATING_MESSAGE)).not.toHaveClass('truncate');
  expect(view.container.querySelectorAll('p[role="status"]')).toHaveLength(0);
  expect(api.post).not.toHaveBeenCalled();
});
