import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { BenchmarkResults, type BenchmarkProblem } from "./BenchmarkResults";

vi.mock("@/lib/api", () => ({ api: { get: vi.fn() } }));

const metric = {
  mae: 100, within_200: 1, tags_micro_f1: 0.8, pending: 0, responded: 2,
  latency_median: 1.2, rating_valid: 2, rating_coverage: 1, rating_failure_rate: 0,
  rating_failures: {}, tags_valid: 2, tags_coverage: 1, tags_failure_rate: 0, tags_failures: {},
};
const result = {
  id: "pilot", label: "Experimento Codeforces 1", version: "v1", split: "development",
  dataset: { version: "v1", split: "development", total: 2, hash: "dataset-hash", seed: 42 },
  prompt: { hash: "prompt-hash" }, intersections: { rating: ["101A", "102B"], tags: ["101A", "102B"] },
  bands: [{ label: "800–1100", total: 1, compared: 1, mae: { baseline: 400, gemini: 100 } }, { label: "1200–1500", total: 1, compared: 1, mae: { baseline: 200, gemini: 100 } }],
  runs: [
    { id: "baseline", provider: "baseline", model: "median", label: "Mediana", metrics: { ...metric, mae: 300, tags_micro_f1: null, tags_coverage: null }, generation_attempts: 0, historical_failures: {} },
    { id: "gemini", provider: "gemini", model: "gemini-test", label: "Gemini sintético", metrics: metric, generation_attempts: 4, historical_failures: { authentication: 2 } },
  ],
  problems: [
    { key: "101A", reference: { rating: 1000, tags: ["math"] }, predictions: {
      baseline: { rating: 1400, rating_status: "valid", tags: null, tags_status: "not_applicable", responded: true },
      gemini: { rating: 1100, rating_status: "valid", tags: ["math"], tags_status: "valid", justification: "Contagem simples", responded: true },
    } },
    { key: "102B", reference: { rating: 1200, tags: ["greedy"] }, predictions: {
      baseline: { rating: 1400, rating_status: "valid", tags: null, tags_status: "not_applicable", responded: true },
      gemini: { rating: 1300, rating_status: "valid", tags: ["greedy"], tags_status: "valid", justification: "Escolha gulosa", responded: true },
    } },
  ],
};

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><BenchmarkResults /></QueryClientProvider>);
}

beforeEach(() => {
  vi.mocked(api.get).mockReset();
  vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
    ? { benchmarks: [{ id: "pilot", label: "Piloto sintético" }, { id: "final", label: "Final sintético" }] }
    : result }) as Awaited<ReturnType<typeof api.get>>);
});
afterEach(cleanup);

describe("Benchmark salvo", () => {
  it("distingue tags inválidas de uma tarefa não aplicável no detalhe", async () => {
    const problems: BenchmarkProblem[] = structuredClone(result.problems);
    const invalid = { ...structuredClone(result), problems };
    invalid.problems[0].predictions.gemini.tags = null;
    invalid.problems[0].predictions.gemini.tags_status = "invalid_output";
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Piloto sintético" }] }
      : invalid }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    await userEvent.setup().click(await screen.findByRole("button", { name: /Oficial 1000, estimado 1100/ }));
    expect(screen.getByText(/Tags estimadas:/)).toHaveTextContent("saída inválida");
  });

  it("mostra qualidade, cobertura e falhas históricas sem chamar IA", async () => {
    mount();
    const row = await within(await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" })).findByRole("row", { name: /Gemini sintético/ });
    expect(within(row).getByText("100,0")).toBeInTheDocument();
    expect(within(row).getByText("2/2 (100%)")).toBeInTheDocument();
    expect(screen.getByText(/authentication: 2/)).not.toBeVisible();
    const rows = screen.getAllByRole("row");
    expect(rows.findIndex(r => r.textContent?.includes("Gemini sintético"))).toBeLessThan(rows.findIndex(r => r.textContent?.includes("Mediana")));
    expect(screen.getByText(/Desenvolvimento/)).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Rating previsto versus oficial/ })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: /Erro médio por faixa/ })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /Problema/ })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Experimento Codeforces 1" })).toBeInTheDocument();
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Ajuda: Erro médio" }));
    expect(await screen.findByRole("tooltip")).toHaveTextContent("distância média");
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(api.get).toHaveBeenCalledWith("/ai-lab/benchmarks/pilot");
  });

  it("permite inspecionar um ponto e trocar o modelo do gráfico", async () => {
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: /Oficial 1200, estimado 1300/ }));
    expect(screen.getByRole("heading", { name: "Problema 102B" })).toBeInTheDocument();
    expect(screen.getByText("Escolha gulosa")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("heading", { name: "Problema 102B" })).not.toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText("Modelo no gráfico"), "baseline");
    expect(screen.getByRole("button", { name: /Oficial 1200, estimado 1400/ })).toBeInTheDocument();
  });

  it("consulta o conjunto selecionado sem executar experimento", async () => {
    const user = userEvent.setup();
    mount();
    await within(await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" })).findByRole("row", { name: /Gemini sintético/ });
    await user.selectOptions(screen.getByLabelText("Conjunto de resultados"), "final");
    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/ai-lab/benchmarks/final"));
  });

  it("explica quando não há resultados publicados", async () => {
    vi.mocked(api.get).mockResolvedValue({ data: { benchmarks: [] } });
    mount();
    expect(await screen.findByText("Nenhum benchmark salvo disponível.")).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("mostra erro de leitura e permite tentar novamente", async () => {
    vi.mocked(api.get).mockRejectedValue(new Error("unavailable"));
    mount();
    expect(await screen.findByRole("alert")).toHaveTextContent("Não foi possível carregar os resultados");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

  it("não apresenta interseção vazia como erro zero", async () => {
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Piloto sintético" }] }
      : { ...result, intersections: { rating: [], tags: [] }, runs: [{ ...result.runs[1], metrics: {
        ...metric, mae: null, within_200: null, rating_valid: 0, rating_coverage: 0,
        rating_failure_rate: 0.5, pending: 1, responded: 1,
      } }] } }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    const row = await within(await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" })).findByRole("row", { name: /Gemini sintético/ });
    expect(within(row).getByText("0/2 (0%)")).toBeInTheDocument();
    expect(screen.getByText(/Nenhum item válido em comum para rating/)).toBeInTheDocument();
  });

  it("mantém valores indisponíveis no fim do ranking", async () => {
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Piloto" }] }
      : { ...result, runs: [{ ...result.runs[1], metrics: { ...metric, mae: null } }, result.runs[0]] }
    }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    const table = await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" });
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("Mediana");
  });
});
