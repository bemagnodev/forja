import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { TooltipProvider } from '@/components/ui/tooltip';
import { ContestResultCell } from './ContestResultCell';
import type { ContestResult } from './types';

const result: ContestResult = { accepted: true, failed_attempts: 0, first_ac_seconds: 181,
  errors_before_ac: {}, errors_after_ac: {}, compilation_errors: 0, coverage: 'complete',
  is_upsolved: false, upsolved_at: null, manual_completion: false };
function mount(changes: Partial<ContestResult> = {}) {
  render(<TooltipProvider><ContestResultCell result={{ ...result, ...changes }} /></TooltipProvider>);
}

it('shows a green plus and HH:MM for the first AC, without +0', () => {
  mount(); expect(screen.getByText('+')).toHaveClass('text-emerald-400');
  expect(screen.getByText('00:03')).toBeVisible(); expect(screen.queryByText('+0')).toBeNull();
});
it('shows failed judgements before AC and truncates seconds', () => {
  mount({ failed_attempts: 2, first_ac_seconds: 4109 });
  expect(screen.getByText('+2')).toBeVisible(); expect(screen.getByText('01:08')).toBeVisible();
});
it('keeps the original minus and adds Upsolvada after practice', () => {
  mount({ accepted: false, failed_attempts: 2, first_ac_seconds: null, is_upsolved: true });
  expect(screen.getByText('−2')).toHaveClass('text-sky-400'); expect(screen.getByText('Upsolvada')).toBeVisible();
  expect(screen.queryByText('+2')).toBeNull();
});
it('shows only a minus for an unattempted problem', () => {
  mount({ accepted: false, first_ac_seconds: null }); expect(screen.getByText('−')).toBeVisible();
});
it('opens verdict details on hover, keyboard focus, and click', async () => {
  mount({ failed_attempts: 2, errors_before_ac: { WA: 1, TLE: 1 }, errors_after_ac: { RE: 1 }, compilation_errors: 2 });
  const button = screen.getByRole('button', { name: /AC no contest/ });
  await userEvent.hover(button); expect(await screen.findByRole('tooltip')).toHaveTextContent('WA: 1');
  expect(screen.getByRole('tooltip')).toHaveTextContent('TLE: 1');
  expect(screen.getByRole('tooltip')).toHaveTextContent('Depois do AC');
  expect(screen.getByRole('tooltip')).toHaveTextContent('CE: 2');
  await userEvent.unhover(button); await userEvent.tab();
  expect(await screen.findByRole('tooltip')).toBeVisible();
});
it('supports touch-style click and labels manual completion without inventing an AC', async () => {
  mount({ accepted: false, first_ac_seconds: null, is_upsolved: true, manual_completion: true });
  await userEvent.click(screen.getByRole('button', { name: /Sem AC no contest/ }));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('Conclusão manual; sem AC confirmado');
  expect(screen.queryByText('+')).toBeNull();
});
it('does not invent attempt counts for partial data', async () => {
  mount({ failed_attempts: null, first_ac_seconds: null, coverage: 'partial' });
  expect(screen.getByText('+?')).toBeVisible(); expect(screen.getByText('—')).toBeVisible();
  await userEvent.click(screen.getByRole('button'));
  expect(await screen.findByRole('tooltip')).toHaveTextContent('Dados parciais');
});
it('does not claim a manual completion or a confirmed post-contest time for a partial imported AC', async () => {
  mount({ accepted: null, first_ac_seconds: null, failed_attempts: null, coverage: 'partial',
    is_upsolved: true, manual_completion: false, upsolved_at: null });
  await userEvent.click(screen.getByRole('button'));
  const tooltip = await screen.findByRole('tooltip');
  expect(tooltip).toHaveTextContent('AC importado; relação temporal com a prova não confirmada');
  expect(tooltip).not.toHaveTextContent('Conclusão manual');
  expect(tooltip).not.toHaveTextContent('AC depois da prova');
});
