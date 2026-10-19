import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Queue } from "./Queue";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import userEvent from "@testing-library/user-event";

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
    
    // Wait for the filters to be rendered (they are shown when not loading and not error)
    await waitFor(() => {
      expect(screen.getByText("TODAS")).toBeInTheDocument();
      expect(screen.getByText("FUTURE")).toBeInTheDocument();
    });
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
