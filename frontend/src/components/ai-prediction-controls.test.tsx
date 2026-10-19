import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { SortableRow } from "./queue/SortableRow";
import { ProblemActionsCell } from "./contests/ProblemActionsCell";
import { TooltipProvider } from "./ui/tooltip";
import type { QueueItem } from "./queue/types";
import type { ContestProblem } from "./contests/types";
import { AxiosError } from 'axios';

const { toast } = vi.hoisted(() => ({ toast: vi.fn() }));

vi.mock("@/lib/api", () => ({ api: { post: vi.fn() } }));
vi.mock("@/components/ui/toast-context", () => ({ useToast: () => ({ toast }) }));
vi.mock("@dnd-kit/sortable", () => ({ useSortable: () => ({
  attributes: {}, listeners: {}, setNodeRef: vi.fn(), transform: null, transition: undefined, isDragging: false,
}) }));
afterEach(cleanup);
beforeEach(() => { vi.mocked(api.post).mockReset(); toast.mockClear(); });

const problem: ContestProblem = { id: 7, platform_id: "7A", title: "Synthetic", index: "A", rating: null,
  ai_rating: null, tags: [], ai_tags: [], url: null, system_status: "UNATTEMPTED", review_status: "PENDING_TRIAGE", tracking_id: null };
const item: QueueItem & { linked_problem_id: number } = { id: 3, item_type: "PROBLEM", title: "Synthetic",
  description: null, source_platform: "CODEFORCES", priority: "P2", is_completed: false, tags: [], order: 0,
  created_at: "2026-10-19T00:00:00Z", resolved_at: null, linked_problem_id: 7 };

function mount(kind: string) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  const invalidate = vi.spyOn(client, "invalidateQueries");
  render(<QueryClientProvider client={client}><TooltipProvider>
    {kind === "queue" ? <table><tbody><SortableRow item={item} onToggle={vi.fn()} onPatchPriority={vi.fn()} onPatchDescription={vi.fn()} /></tbody></table>
      : <ProblemActionsCell problem={problem} />}
  </TooltipProvider></QueryClientProvider>);
  return invalidate;
}

it.each(["queue", "contest"])("%s usa a rota canônica e atualiza fila e contests", async kind => {
  vi.mocked(api.post).mockResolvedValue({ data: { rating: 1200, tags: ["math"], cached: false } });
  const user = userEvent.setup();
  const invalidate = mount(kind);
  expect(api.post).not.toHaveBeenCalled();
  await user.click(screen.getByTitle(/Estimar rating e tags com IA/));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/problems/7/predict", null, { params: { force: "false" } }));
  await waitFor(() => {
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["queue"] });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["contest-problems"] });
  });
  expect(api.post).toHaveBeenCalledTimes(1);
});

it.each(["queue", "contest"])("%s preserva Shift+click para recálculo explícito", async kind => {
  vi.mocked(api.post).mockResolvedValue({ data: { rating: 1200, tags: ["math"] } });
  const user = userEvent.setup();
  mount(kind);
  await user.keyboard("{Shift>}");
  await user.click(screen.getByTitle(/Estimar rating e tags com IA/));
  await user.keyboard("{/Shift}");
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/problems/7/predict", null, { params: { force: "true" } }));
  expect(api.post).toHaveBeenCalledTimes(1);
});

it("a fila não cria botões aninhados no seletor de prioridade", () => {
  mount("queue");
  expect(document.querySelector("button button")).toBeNull();
});

it.each(['queue', 'contest'])('%s preserves backend failure details without repeating or invalidating data', async kind => {
  const error = new AxiosError('Request failed');
  Object.assign(error, { response: { status: 502, data: { detail: 'O site respondeu HTTP 403. A IA não foi chamada.',
    diagnostic: { stage: 'fetch', code: 'source_http_error', request_id: 'trace-id' } } } });
  vi.mocked(api.post).mockRejectedValue(error);
  const invalidate = mount(kind);
  await userEvent.setup().click(screen.getByTitle(/Estimar rating e tags com IA/));
  await waitFor(() => expect(toast).toHaveBeenCalledWith(expect.objectContaining({ type: 'error',
    description: expect.stringContaining('A IA não foi chamada. Código: trace-id') })));
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(invalidate).not.toHaveBeenCalled();
});
