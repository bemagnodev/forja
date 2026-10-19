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
  it("exibe e copia os prompts registrados sem executar IA", async () => {
    const user = userEvent.setup();
    const copy = vi.spyOn(navigator.clipboard, "writeText").mockResolvedValue();
    const prompts = [
      { version: "classification_v1", label: "Classificação direta", description: "Sem exemplos.", hash: "hash-a", text: "Instrução registrada <script>não executar</script>" },
      { version: "classification_v2", label: "Classificação com rubrica", description: "Critérios explícitos, sem exemplos.", hash: "hash-b", text: "Instrução com critérios e taxonomia preenchida" },
    ];
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Comparação" }] }
      : { ...result, prompts, selection_note: "Escolhido pelo menor MAE em classificação direta, cobertura mínima de 95%." }
    }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    await screen.findByRole("heading", { name: result.label });
    expect(screen.getByLabelText("Prompt completo")).not.toBeVisible();
    await user.click(screen.getByText("Técnica e prompt"));
    expect(screen.getByLabelText("Prompt completo")).toHaveTextContent(prompts[0].text);
    expect(screen.getByLabelText("Prompt completo").querySelector("script")).toBeNull();
    await user.click(screen.getByRole("button", { name: "Copiar prompt" }));
    expect(copy).toHaveBeenCalledWith(prompts[0].text);
    await user.selectOptions(screen.getByLabelText("Estratégia do prompt", { exact: true }), "hash-b");
    expect(screen.getByLabelText("Prompt completo")).toHaveTextContent(prompts[1].text);
    expect(screen.getByText(/Escolhido pelo menor MAE/)).toBeVisible();
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it("mostra cobertura das tags junto do F1 e distingue duração de cadência", async () => {
    mount();
    const table = await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" });
    const row = within(table).getByRole("row", { name: /Gemini sintético/ });
    expect(within(row).getByText("Tags válidas: 2/2")).toBeVisible();
    await userEvent.setup().click(screen.getByText("Detalhes da avaliação"));
    expect(screen.getByText(/Não inclui a cadência entre chamadas nem as pausas de retomada/)).toBeVisible();
  });

  it("mostra a amostra real por faixa no conjunto final sem chamá-lo de piloto", async () => {
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "final", label: "Final" }] }
      : { ...result, dataset: { ...result.dataset, split: "final", total: 60 },
        bands: result.bands.map(band => ({ ...band, total: 15, compared: 15 })) }
    }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    expect(await screen.findByText(/Amostra: 15 problemas selecionados por faixa/)).toBeInTheDocument();
    expect(screen.queryByText(/Piloto exploratório: 3 problemas/)).not.toBeInTheDocument();
  });

  it.each<[string[], string]>([
    [["classification_v1"], "Prompt A (v1)"],
    [["classification_v2"], "Prompt B (v2)"],
    [["classification_v1", "classification_v2"], "Prompts A (v1) e B (v2)"],
    [[], "Versão do prompt não informada"],
  ])("identifica os prompts reais da comparação: %j", async (versions, label) => {
    const runs = [result.runs[0], ...((versions.length ? versions : [undefined]).map((version, index) => ({
      ...result.runs[1], id: `model-${index}`, prompt_version: version,
    })))];
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Piloto" }] }
      : { ...result, runs, prompt: { hash: versions.length > 1 ? null : "prompt-hash" } }
    }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    expect(await screen.findByText(new RegExp(`Desenvolvimento · resultado exploratório · ${String(label).replace(/[()]/g, "\\$&")}`))).toBeInTheDocument();
    expect(screen.queryByText(/Mesmos enunciados preparados e prompt v1/)).not.toBeInTheDocument();
    if (versions.length > 1) expect(screen.getByText(/Prompt por execução/)).toBeInTheDocument();
  });

  it("usa escala fixa de mil pontos sem alterar o MAE exibido", async () => {
    mount();
    const table = await screen.findByRole("table", { name: "Comparação de qualidade e cobertura dos modelos" });
    expect(within(table).getByRole("meter", { name: "Erro médio: Gemini sintético" })).toHaveAttribute("aria-valuemax", "1000");
    expect(within(table).getByRole("meter", { name: "Erro médio: Gemini sintético" })).toHaveAttribute("aria-valuenow", "100");
    expect(within(table).getByRole("meter", { name: "Erro médio: Mediana" }).firstElementChild).toHaveStyle({ width: "30%" });
  });

  it("preserva o número quando o erro ultrapassa a escala visual", async () => {
    vi.mocked(api.get).mockImplementation(async (url) => ({ data: url === "/ai-lab/benchmarks"
      ? { benchmarks: [{ id: "pilot", label: "Piloto" }] }
      : { ...result, runs: [{ ...result.runs[1], metrics: { ...metric, mae: 1200 } }] }
    }) as Awaited<ReturnType<typeof api.get>>);
    mount();
    const meter = await screen.findByRole("meter", { name: "Erro médio: Gemini sintético" });
    expect(meter).toHaveAttribute("aria-valuetext", "1200 pontos; acima da escala visual de 1000 pontos");
    expect(meter.firstElementChild).toHaveStyle({ width: "100%" });
    expect(screen.getByText("1.200,0")).toBeInTheDocument();
  });

  it("explica F1 micro e informa o conjunto válido de tags", async () => {
    mount();
    await userEvent.setup().click(await screen.findByRole("button", { name: "Ajuda: F1 de tags" }));
    const help = await screen.findByRole("tooltip");
    expect(help).toHaveTextContent("extras e as que faltaram");
    expect(help).toHaveTextContent("Não representa a porcentagem de problemas totalmente corretos");
    expect(screen.getByText("Tags comparadas em 2/2 problemas")).toBeVisible();
  });

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
