import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Queue } from './Queue';

const mocks = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), toast: vi.fn(), drag: null as null | ((event: unknown) => void) }));
vi.mock('@/lib/api', () => ({ api: mocks }));
vi.mock('@/components/ui/toast-context', () => ({ useToast: () => ({ toast: mocks.toast }) }));
vi.mock('@dnd-kit/core', async importOriginal => ({ ...await importOriginal<object>(), DndContext: ({ children, onDragEnd }: { children: React.ReactNode; onDragEnd: typeof mocks.drag }) => { mocks.drag = onDragEnd; return children; } }));
vi.mock('@/components/queue/SortableRow', () => ({ SortableRow: ({ item, onToggle, onPatchDescription }: { item: { id: number; title: string; is_completed: boolean }; onToggle: (id: number, done: boolean, title: string) => void; onPatchDescription: (id: number, text: string) => Promise<void> }) => <tr><td>{item.title}<button onClick={() => onToggle(item.id, item.is_completed, item.title)}>Concluir {item.title}</button><button onClick={() => { void onPatchDescription(item.id, 'nota').catch(() => undefined); }}>Editar {item.title}</button></td></tr> }));

function deferred() { let resolve!: (value: unknown) => void; let reject!: (error: Error) => void; const promise = new Promise((a, b) => { resolve = a; reject = b; }); return { promise, resolve, reject }; }
const items = [{ id: 1, title: 'Primeiro', is_completed: false, priority: 'P1' }, { id: 2, title: 'Segundo', is_completed: false, priority: 'P2' }];
function mount() { const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }); render(<QueryClientProvider client={client}><Queue /></QueryClientProvider>); return client; }
beforeEach(() => { vi.clearAllMocks(); mocks.get.mockResolvedValue({ data: items }); });

it('não remove nem anuncia conclusão enquanto pendente; mantém item no erro', async () => {
  const request = deferred(); mocks.post.mockReturnValue(request.promise); mount();
  await userEvent.click(await screen.findByRole('button', { name: 'Concluir Primeiro' }));
  await userEvent.click(screen.getByRole('button', { name: 'Concluir Primeiro' }));
  expect(mocks.post).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Primeiro')).toBeVisible(); expect(mocks.toast).not.toHaveBeenCalled();
  await act(async () => request.reject(new Error('timeout')));
  expect(screen.getByText('Primeiro')).toBeVisible();
  expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' }));
});

it('confirma conclusão antes de oferecer desfazer; falha do desfazer preserva conclusão', async () => {
  const client = mount(); await screen.findByText('Primeiro');
  mocks.post.mockResolvedValueOnce({ data: {} });
  mocks.get.mockResolvedValue({ data: items.map(i => i.id === 1 ? { ...i, is_completed: true } : i) });
  await userEvent.click(screen.getByRole('button', { name: 'Concluir Primeiro' }));
  await waitFor(() => expect(screen.queryByText('Primeiro')).not.toBeInTheDocument());
  const notice = mocks.toast.mock.calls.find(([x]) => x.type === 'success')![0];
  mocks.post.mockRejectedValueOnce(new Error('500'));
  await act(async () => notice.action.onClick());
  await waitFor(() => expect(mocks.toast).toHaveBeenLastCalledWith(expect.objectContaining({ type: 'error' })));
  expect(client.getQueryData<typeof items>(['queue'])!.find(i => i.id === 1)!.is_completed).toBe(true);
});

it('restaura a ordem após falha de reordenação e informa o erro', async () => {
  const client = mount(); await screen.findByText('Primeiro'); const request = deferred(); mocks.post.mockReturnValue(request.promise);
  await act(async () => mocks.drag!({ active: { id: 1 }, over: { id: 2 } }));
  await waitFor(() => expect(client.getQueryData<typeof items>(['queue'])![0].id).toBe(2));
  await act(async () => request.reject(new Error('500')));
  await waitFor(() => expect(client.getQueryData<typeof items>(['queue'])![0].id).toBe(1));
  expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' }));
});

it('falha de arraste não substitui dados mais recentes pelo snapshot antigo', async () => {
  const client = mount(); await screen.findByText('Primeiro');
  const request = deferred(); mocks.post.mockReturnValue(request.promise);
  await act(async () => mocks.drag!({ active: { id: 1 }, over: { id: 2 } }));
  const newer = [{ ...items[0], title: 'Título atualizado' }, items[1]];
  mocks.get.mockResolvedValue({ data: newer });
  act(() => client.setQueryData(['queue'], newer));
  await act(async () => request.reject(new Error('500')));
  await waitFor(() => expect(screen.getByText('Título atualizado')).toBeVisible());
  expect(client.getQueryData(['queue'])).toEqual(newer);
});

it('preserva formulário e impede envio duplicado enquanto a criação está pendente', async () => {
  const request = deferred(); mocks.post.mockReturnValue(request.promise); mount(); const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: 'Novo Item' })); await user.click(screen.getByRole('button', { name: 'Estudo' }));
  await user.type(screen.getByPlaceholderText('Ex: Estudar DP em árvores, Segment Tree lazy'), 'Revisar DP');
  await user.click(screen.getByRole('button', { name: 'Criar Item' }));
  expect(screen.getByRole('dialog')).toBeVisible(); expect(screen.getByRole('button', { name: /Criando|Criar Item/ })).toBeDisabled();
  await act(async () => request.reject(new Error('500')));
  expect(screen.getByDisplayValue('Revisar DP')).toBeVisible(); expect(mocks.post).toHaveBeenCalledTimes(1);
  mocks.post.mockResolvedValueOnce({ data: {} }); await user.click(screen.getByRole('button', { name: 'Criar Item' }));
  await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
});

it('informa erro de edição sem atualizar o valor salvo', async () => {
  mocks.patch.mockRejectedValue(new Error('500')); const client = mount();
  await userEvent.click(await screen.findByRole('button', { name: 'Editar Primeiro' }));
  await waitFor(() => expect(mocks.toast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error' })));
  expect(client.getQueryData(['queue'])).toEqual(items);
});
