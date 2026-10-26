import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { ActivityHeatmap } from './ActivityHeatmap';

afterEach(() => { cleanup(); vi.useRealTimers(); });

it('preserva os 365 dias em uma malha que cabe na largura do card', () => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-10-25T12:00:00Z'));
  render(<ActivityHeatmap data={[{ date: '2026-10-25', count: 3 }]} />);
  const grid = screen.getByRole('img', { name: /atividade.*365 dias/i });
  expect(grid.querySelectorAll('[title]')).toHaveLength(365);
  expect(screen.getByTitle('2025-10-26: 0 submissões')).toBeInTheDocument();
  expect(screen.getByTitle('2026-10-25: 3 submissões')).toBeInTheDocument();
  expect(grid).toHaveClass('w-full');
  expect(grid.style.gridAutoColumns).toBe('minmax(0, 1fr)');
  expect(grid.querySelector('[class*="w-[14px]"]')).toBeNull();
  expect(grid.closest('.overflow-x-auto')).toBeNull();
});
