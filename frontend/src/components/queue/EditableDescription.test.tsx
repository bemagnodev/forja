import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import { EditableDescription } from './EditableDescription';

it('distingue descrição ausente de texto salvo e abre um campo vazio', async () => {
  render(<EditableDescription value={null} onSave={vi.fn()} />);
  const button = screen.getByRole('button', { name: 'Adicionar descrição' });
  expect(button).toHaveTextContent('—');
  expect(screen.queryByText('Adicionar nota')).toBeNull();
  await userEvent.click(button);
  expect(screen.getByRole('textbox', { name: 'Editar descrição' })).toHaveValue('');
});

it('preserva a nota existente e usa texto claro durante a edição', async () => {
  const save = vi.fn().mockResolvedValue(undefined);
  render(<EditableDescription value="Revisar invariantes" onSave={save} />);
  await userEvent.click(screen.getByRole('button', { name: 'Editar descrição' }));
  const input = screen.getByRole('textbox', { name: 'Editar descrição' });
  expect(input).toHaveValue('Revisar invariantes');
  expect(input).toHaveClass('text-white/80');
  await userEvent.type(input, ' e limites{Enter}');
  expect(save).toHaveBeenCalledWith('Revisar invariantes e limites');
});
