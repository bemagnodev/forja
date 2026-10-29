import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Queue } from "./Queue";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";
import { api } from '@/lib/api';

// Mock das dependências e da API
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn().mockResolvedValue({ data: [] }),
    patch: vi.fn(),
  }
}));

vi.mock("@/components/ui/toast-context", () => ({
  useToast: () => ({ toast: vi.fn() })
}));

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
});

describe("Queue Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    queryClient.clear();
    vi.mocked(api.get).mockResolvedValue({ data: [] });
  });

  it("abre e cancela Novo Item sem criar botões aninhados", async () => {
    const user = userEvent.setup();
    render(<QueryClientProvider client={queryClient}><Queue /></QueryClientProvider>);
    expect(document.querySelector("button button")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Novo Item" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(document.querySelector("button button")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("renders the queue and filter buttons", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Queue />
      </QueryClientProvider>
    );
    expect(screen.getByRole('heading', { name: 'Fila' })).toBeInTheDocument();
    expect(screen.getByText('Organize suas questões e sessões de treinamento')).toBeInTheDocument();
    
    // Wait for the filters to be rendered (they are shown when not loading and not error)
    await waitFor(() => {
      expect(screen.getByText("TODAS")).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Futuro' })).toHaveAttribute('aria-pressed', 'false');
    });
  });

  it('distingue filtro sem resultados da fila inteira e permite limpar o filtro', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: [{ id: 1, title: 'Estudar grafos', item_type: 'STUDY_SESSION', priority: 'P1', tags: [], is_completed: false }] });
    render(<QueryClientProvider client={queryClient}><Queue /></QueryClientProvider>);
    await screen.findByText('Estudar grafos');
    await userEvent.click(screen.getByRole('button', { name: 'P2' }));
    expect(screen.getByRole('button', { name: 'P2' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByText('Nenhum item nesta prioridade.')).toBeVisible();
    expect(screen.queryByText(/completamente paga/)).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Limpar filtro' }));
    expect(await screen.findByText('Estudar grafos')).toBeVisible();
  });

  it("can toggle group by contest", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <Queue />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText("TODAS")).toBeInTheDocument();
    });

    const checkbox = screen.getByRole("checkbox");
    fireEvent.click(checkbox);
    
    expect(checkbox).toBeChecked();
  });
});
