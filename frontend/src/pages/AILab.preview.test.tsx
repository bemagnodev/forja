import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { AILab } from './AILab';
import { api } from '@/lib/api';

vi.mock('@/lib/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock('@/lib/visual-preview', () => ({ visualPreview: true }));
vi.mock('@/components/ai-lab/BenchmarkResults', () => ({ BenchmarkResults: () => null }));

it('carrega um exemplo real da base local e compara a simulação escolhida com a referência', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [
    { id: 70, platform_id: '999900D', title: 'Exemplo com referência', platform: 'CF_GYM' },
    { id: 71, platform_id: '999900C', title: 'Exemplo sem referência', platform: 'CF_GYM' },
  ] });
  vi.mocked(api.post).mockResolvedValue({ data: { rating: 1500, real_rating: 1300, real_tags: ['math'],
    tags: ['graphs'], rating_status: 'valid', tags_status: 'valid', reasoning: 'Simulação local',
    model: 'gemini-3.5-flash-lite', discarded_tags_count: 0 } });
  const user = userEvent.setup();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><AILab /></QueryClientProvider>);
  await user.click(await screen.findByRole('button', { name: 'Com rating oficial' }));
  await user.selectOptions(screen.getByLabelText('Cenário da prévia'), 'overestimate');
  await user.click(screen.getByRole('button', { name: 'Classificar questão' }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith('/ai-lab/problems/70/classify', null,
    { params: { model_name: 'gemini-3.5-flash-lite', preview_scenario: 'overestimate' } }));
  expect(await screen.findByLabelText('Rating oficial')).toHaveTextContent('1300');
  expect(screen.getByLabelText('Rating estimado')).toHaveTextContent('1500');
});
