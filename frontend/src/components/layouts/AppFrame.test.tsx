import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { AppFrame } from './AppFrame';

it('opens the mobile navigation and closes on Escape, returning focus', async () => {
  render(<AppFrame sidebar={<a href="#contests">Contests</a>}><p>Conteúdo</p></AppFrame>);
  await userEvent.click(screen.getByRole('button', { name: 'Abrir menu' }));
  expect(screen.getByRole('button', { name: 'Fechar menu' })).toHaveAttribute('aria-expanded', 'true');
  await userEvent.keyboard('{Escape}');
  expect(screen.getByRole('button', { name: 'Abrir menu' })).toHaveFocus();
});
it('closes navigation when selecting a route without removing page content', async () => {
  render(<AppFrame sidebar={<a href="#contests">Contests</a>}><p>Conteúdo</p></AppFrame>);
  await userEvent.click(screen.getByRole('button', { name: 'Abrir menu' }));
  await userEvent.click(screen.getByRole('link', { name: 'Contests' }));
  expect(screen.getByRole('button', { name: 'Abrir menu' })).toHaveAttribute('aria-expanded', 'false');
  expect(screen.getByText('Conteúdo')).toBeVisible();
});
