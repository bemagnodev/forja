import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { Queue } from './Queue';

vi.mock('@/lib/api', () => ({ api: { get: vi.fn().mockResolvedValue({ data: [] }) } }));
vi.mock('@/lib/visual-preview', () => ({ visualPreview: true }));
vi.mock('@/components/ui/toast-context', () => ({ useToast: () => ({ toast: vi.fn() }) }));

it('não oferece mais a faixa de prioridade na prévia', async () => {
  render(<QueryClientProvider client={new QueryClient()}><Queue /></QueryClientProvider>);
  await screen.findByRole('heading', { name: 'Fila' });
  expect(screen.queryByRole('checkbox', { name: 'Faixa de prioridade' })).toBeNull();
});
