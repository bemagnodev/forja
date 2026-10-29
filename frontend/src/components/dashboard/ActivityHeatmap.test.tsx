import { cleanup, render, screen, within } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { ActivityHeatmap } from './ActivityHeatmap';

afterEach(() => { cleanup(); vi.useRealTimers(); });

it('não sobrepõe o mês inicial quase encerrado ao rótulo do mês seguinte', () => {
  render(<ActivityHeatmap referenceDate="2026-10-29" data={[]} />);
  expect(screen.getAllByText('out')).toHaveLength(1);
  expect(screen.getByText('nov')).toBeVisible();
});

it('não quebra a página se a data de referência ainda não veio da API', () => {
  render(<ActivityHeatmap referenceDate="" data={[]} />);
  expect(screen.getByText(/Calendário indisponível/)).toBeVisible();
});

it('preserva os 365 dias em uma malha que cabe na largura do card', () => {
  vi.useFakeTimers({ toFake: ['Date'] });
  vi.setSystemTime(new Date('2026-10-25T12:00:00Z'));
  render(<ActivityHeatmap data={[{ date: '2026-10-25', count: 3 }]} referenceDate="2026-10-25" />);
  const grid = screen.getByRole('img', { name: /atividade.*365 dias/i });
  expect(grid.querySelectorAll('[title]')).toHaveLength(365);
  expect(screen.getByTitle('2025-10-26: 0 submissões aceitas')).toBeInTheDocument();
  expect(screen.getByTitle('2026-10-25: 3 submissões aceitas')).toBeInTheDocument();
  expect(grid).toHaveClass('w-full');
  expect(within(grid).getByText('Dom').style.gridRow).toBe('1');
  expect(screen.getByTitle('2026-10-25: 3 submissões aceitas').style.gridRow).toBe('1');
  expect(grid.querySelector('[class*="w-[14px]"]')).toBeNull();
  expect(grid.closest('.overflow-x-auto')).toBeNull();
});


it('alinha semanas e ignora dados fora do recorte sem depender do relógio do navegador', () => {
  render(<ActivityHeatmap referenceDate="2024-02-29" data={[{ date: '2024-02-29', count: 2 }, { date: '2024-03-01', count: 5 }, { date: '2023-02-28', count: 1 }]} />);
  const grid = screen.getByRole('img', { name: /atividade.*365 dias/i });
  expect(grid.querySelectorAll('[title]')).toHaveLength(365);
  expect(grid.querySelectorAll('[data-calendar-padding]')).toHaveLength(6);
  expect(screen.getByTitle('2023-03-02: 0 submissões aceitas')).toBeInTheDocument();
  expect(screen.getByTitle('2024-02-29: 2 submissões aceitas')).toBeInTheDocument();
  expect(screen.getByText('1 dias ativos')).toBeInTheDocument();
  expect(screen.getByText('Dom')).toBeInTheDocument();
  expect(screen.getAllByText('fev').length).toBeGreaterThan(0);
});
