import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { SortableRow } from "./queue/SortableRow";
import { TooltipProvider } from "./ui/tooltip";
import { ContestDetail } from "@/pages/ContestDetail";
import { AILab } from "@/pages/AILab";
import type { QueueItem } from "./queue/types";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
vi.mock("@/components/ui/toast-context", () => ({ useToast: () => ({ toast: vi.fn() }) }));
vi.mock("@dnd-kit/sortable", () => ({ useSortable: () => ({
  attributes: {}, listeners: {}, setNodeRef: vi.fn(), transform: null, transition: undefined, isDragging: false,
}) }));
afterEach(cleanup);
beforeEach(() => vi.clearAllMocks());
const warning = "Esta questão contém imagens que não foram analisadas; a estimativa pode ser menos precisa.";
const problem = { id: 7, platform_id: "7A", title: "Synthetic", index: "A", rating: null,
  ai_rating: 3500, tags: [], ai_tags: ["math"], ai_visual_status: "unprocessed", url: null,
  system_status: "UNATTEMPTED", review_status: "PENDING_TRIAGE", tracking_id: null };
const item: QueueItem = { id: 3, item_type: "PROBLEM", title: "Synthetic", description: null,
  source_platform: "CODEFORCES", priority: "P2", is_completed: false, tags: [], order: 0,
  created_at: "2026-10-19T00:00:00Z", resolved_at: null, linked_problem_id: 7,
  ai_rating: 3500, ai_tags: ["math"], ai_visual_status: "unprocessed" };

function mount(kind: "queue" | "contest" | "explore") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><TooltipProvider>
    {kind === "queue" ? <table><tbody><SortableRow item={item} onToggle={vi.fn()} onPatchPriority={vi.fn()} onPatchDescription={vi.fn()} /></tbody></table>
      : kind === "contest" ? <MemoryRouter initialEntries={["/contests/1"]}><Routes><Route path="/contests/:id" element={<ContestDetail />} /></Routes></MemoryRouter>
      : <AILab />}
  </TooltipProvider></QueryClientProvider>);
}

it.each(["queue", "contest"] as const)("%s mostra rating 3500 e aviso salvo, inclusive após remontar", async kind => {
  vi.mocked(api.get).mockResolvedValue({ data: [problem] });
  const first = mount(kind);
  expect(await screen.findByText(warning)).toBeVisible();
  expect(screen.getByText("3500")).toBeVisible();
  expect(document.querySelector("button button")).toBeNull();
  first.unmount();
  mount(kind);
  expect(await screen.findByText(warning)).toBeVisible();
  expect(api.post).not.toHaveBeenCalled();
});

it("Explorar exibe aviso textual e permite inspecionar e recolher dados do scraper", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [{ id: 7, platform: "CF_OFFICIAL", platform_id: "7A", title: "Synthetic" }] });
  vi.mocked(api.post).mockResolvedValue({ data: { rating: 3500, tags: ["math"], reasoning: "Text estimate",
    model: "gemini-3.5-flash-lite", rating_status: "valid", tags_status: "valid", visual_status: "unprocessed",
    discarded_tags_count: 0, raw_data: { description: "TEXT_WITH_IMAGE_MARKER [image:1]" } } });
  const user = userEvent.setup();
  mount("explore");
  await user.type(screen.getByPlaceholderText(/Busque por ID/), "7A");
  await user.click(await screen.findByText("Synthetic"));
  await user.click(screen.getByRole("button", { name: /Categorizar/ }));
  expect(await screen.findByText(warning)).toBeVisible();
  expect(screen.getByText("3500")).toBeVisible();
  const details = screen.getByRole("button", { name: "Dados Brutos do Scraper" });
  await user.click(details);
  expect(await screen.findByText(/TEXT_WITH_IMAGE_MARKER/)).toBeVisible();
  await user.click(details);
  expect(details).toHaveAttribute("aria-expanded", "false");
  expect(api.post).toHaveBeenCalledTimes(1);
  expect(api.post).toHaveBeenCalledWith("/ai-lab/problems/7/classify", null,
    { params: { model_name: "gemini-3.5-flash-lite" } });
});
