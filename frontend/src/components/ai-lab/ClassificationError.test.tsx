import { AxiosError } from 'axios';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import { ClassificationError } from './ClassificationError';

afterEach(cleanup);
it('shows a useful message and copies only safe backend diagnostics', async () => {
  const user = userEvent.setup();
  const copy = vi.spyOn(navigator.clipboard, 'writeText').mockResolvedValue();
  const error = new AxiosError('Request failed');
  Object.assign(error, { response: { status: 502, data: {
    detail: 'O site respondeu HTTP 403. A IA não foi chamada.',
    diagnostic: { stage: 'fetch', code: 'source_http_error', model: 'gemini-test', platform: 'CF_OFFICIAL',
      upstream_status: 403, request_id: 'safe-id', source_category: 'cloudflare_challenge',
      source_cf_ray: 'a4d111ae5e63e0e3-GIG', secret: 'PRIVATE' }, secret: 'PRIVATE' } } });
  render(<ClassificationError error={error} />);
  expect(screen.getByText(/A IA não foi chamada/)).toBeVisible();
  await user.click(screen.getByText('Detalhes técnicos'));
  expect(screen.getByText('safe-id')).toBeVisible();
  await user.click(screen.getByRole('button', { name: 'Copiar diagnóstico' }));
  const copied = copy.mock.calls[0][0];
  expect(copied).toContain('source_http_error');
  expect(copied).toContain('a4d111ae5e63e0e3-GIG');
  expect(copied).not.toContain('PRIVATE');
});

it('does not display proxy HTML or claim every failure is temporary', () => {
  const error = new AxiosError('Request failed');
  Object.assign(error, { response: { status: 502, data: '<html>PRIVATE</html>' } });
  render(<ClassificationError error={error} />);
  expect(screen.getByRole('alert')).toHaveTextContent('HTTP 502');
  expect(screen.queryByText(/PRIVATE/)).not.toBeInTheDocument();
});
