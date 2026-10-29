import { useState } from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it } from 'vitest';
import { SelectControl } from './select-control';

function Example() {
  const [value, setValue] = useState('all');
  return <SelectControl label="Tipo de participação" value={value} onValueChange={setValue}
    options={[{ value: 'all', label: 'Oficiais e virtuais' }, { value: 'virtual', label: 'Virtuais' }, { value: 'official', label: 'Oficiais' }]} />;
}

it('permite escolher uma opção e devolve o foco ao seletor', async () => {
  const user = userEvent.setup(); render(<Example />);
  const trigger = screen.getByRole('combobox', { name: 'Tipo de participação' });
  expect(trigger).toHaveTextContent('Oficiais e virtuais');
  await user.click(trigger);
  await user.click(await screen.findByRole('option', { name: 'Virtuais' }));
  expect(trigger).toHaveTextContent('Virtuais');
  expect(trigger).toHaveFocus();
});

it('preserva a escolha ao fechar com Escape e permite navegação por teclado', async () => {
  const user = userEvent.setup(); render(<Example />);
  const trigger = screen.getByRole('combobox', { name: 'Tipo de participação' });
  await user.tab(); await user.keyboard('{Enter}');
  expect(await screen.findByRole('listbox')).toBeVisible();
  await user.keyboard('{Escape}');
  expect(trigger).toHaveFocus(); expect(trigger).toHaveTextContent('Oficiais e virtuais');
  await user.keyboard('{Enter}');
  await screen.findByRole('listbox');
  await user.keyboard('{ArrowDown}');
  await user.keyboard('{Enter}');
  expect(trigger).toHaveTextContent('Virtuais');
});
