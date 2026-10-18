import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AILab } from "./AILab";

vi.mock("@/components/ai-lab/BenchmarkResults", () => ({ BenchmarkResults: () => <p>Comparação salva</p> }));
vi.mock("@/lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
afterEach(cleanup);

it("abre em Explorar e permite acessar o benchmark sem inferência", async () => {
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AILab /></QueryClientProvider>);
  expect(screen.getByRole("tab", { name: "Explorar" })).toHaveAttribute("aria-selected", "true");
  expect(screen.getAllByRole("tab")[0]).toHaveTextContent("Explorar");
  for (const platform of ["CODEFORCES", "ATCODER", "CSES"]) {
    expect(screen.getByRole("img", { name: platform })).toBeInTheDocument();
  }
  expect(screen.getByText("Configurar Predição")).toBeInTheDocument();
  expect(screen.queryByText("Comparação salva")).not.toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Benchmark" }));
  expect(screen.getByText("Comparação salva")).toBeInTheDocument();
  expect(screen.queryByText("Configurar Predição")).not.toBeInTheDocument();
});
