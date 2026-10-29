import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { ContestCard, type ContestParticipation } from './ContestCard';
import { ContestEvolution } from './ContestEvolution';
import { CompactProblemTags } from './CompactProblemTags';
import { TooltipProvider } from '@/components/ui/tooltip';

const part: ContestParticipation = { id: 1, contest_id: 42, contest_name: 'Treino de equipe',
  contest_platform: 'CF_GYM', participation_date: '2026-10-25T12:00:00Z', is_virtual: true,
  has_debt: false, progress: { solved_live: 6, upsolved: 1, pending_upsolve: 0, unattempted: 5, total: 12 },
  url: null, rank: 11, rank_context: 'VIRTUAL', penalty: 700, solve_count: 0, upsolve_count: 0, total_problems: 12 };

it('uses a numeric date, platform logo and participant label without a redundant call to action', () => {
  render(<MemoryRouter><ContestCard participation={part} /></MemoryRouter>);
  expect(screen.getByText('25/10/2026')).toBeVisible();
  expect(screen.getByRole('img', { name: 'Codeforces' })).toBeVisible();
  expect(screen.getByText('Equipe')).toBeVisible();
  expect(screen.queryByText('Ver questões e resultados')).toBeNull();
});

it('keeps tags compact while exposing the entire list on click', async () => {
  render(<TooltipProvider><CompactProblemTags tags={['dp', 'graphs', 'math', 'greedy']} /></TooltipProvider>);
  expect(screen.getByText('+2')).toBeVisible();
  expect(screen.queryByText('greedy')).toBeNull();
  await userEvent.click(screen.getByRole('button', { name: 'Todas as tags' }));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('greedy');
});

it('shows dated contest results and preserves absent rankings without a penalty comparison', async () => {
  render(<ContestEvolution participations={[part, { ...part, id: 2, contest_id: 43, contest_name: 'Sem placar', rank_context: '', rank: null, penalty: null }]} />);
  expect(screen.getByRole('heading', { name: 'Resultados por contest' })).toBeVisible();
  expect(screen.getAllByText('25/10')).toHaveLength(2);
  expect(screen.queryByRole('tab', { name: 'Penalidade' })).toBeNull();
  await userEvent.click(screen.getByRole('tab', { name: 'Ranking' }));
  expect(screen.getByText('Menor posição é melhor')).toBeVisible();
  expect(screen.getByRole('button', { name: /Sem placar: ranking indisponível/ })).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: /Treino de equipe: posição 11/ }));
  expect(screen.getByRole('status')).toHaveTextContent('#11');
  await userEvent.keyboard('{Home}');
  await userEvent.click(screen.getByRole('tab', { name: 'Resoluções' }));
  await userEvent.click(screen.getByLabelText('Percentual'));
  expect(screen.getByRole('button', { name: /Treino de equipe: 6 ACs na prova de 12 questões/ })).toBeVisible();
});
