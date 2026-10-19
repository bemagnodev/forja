import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { AILab } from "./AILab";
import { api } from "@/lib/api";
import { AxiosError } from 'axios';

vi.mock("@/components/ai-lab/BenchmarkResults", () => ({ BenchmarkResults: () => <p>Comparação salva</p> }));
vi.mock("@/lib/api", () => ({ api: { get: vi.fn(), post: vi.fn() } }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it('shows extraction diagnostics in Explore without retrying the classification', async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [{ id: 7, platform: 'CF_OFFICIAL', platform_id: '7A', title: 'Synthetic' }] });
  vi.mocked(api.post).mockReset();
  const error = new AxiosError('Request failed');
  Object.assign(error, { response: { status: 400, data: { detail: 'O enunciado está incompleto. A IA não foi chamada.',
    diagnostic: { stage: 'prepare', code: 'statement_incomplete', request_id: 'explore-trace' } } } });
  vi.mocked(api.post).mockRejectedValue(error);
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AILab /></QueryClientProvider>);
  await user.type(screen.getByPlaceholderText(/Busque por ID/), '7A');
  await user.click(await screen.findByText('Synthetic'));
  await user.click(screen.getByRole('button', { name: /Categorizar/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('A IA não foi chamada.');
  await user.click(screen.getByText('Detalhes técnicos'));
  expect(screen.getByText('explore-trace')).toBeVisible();
  expect(api.post).toHaveBeenCalledTimes(1);
});

it("classifica com o modelo escolhido e limpa a previsão ao trocar a seleção", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [{ id: 7, platform: "CF_OFFICIAL", platform_id: "7A", title: "Synthetic problem" }] });
  vi.mocked(api.post).mockResolvedValue({ data: { rating: 1200, tags: ["math"], reasoning: "Justificativa sintética", real_rating: null, real_tags: [], model: "openai/gpt-oss-20b", rating_status: "valid", tags_status: "valid", discarded_tags_count: 0 } });
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AILab /></QueryClientProvider>);
  expect(screen.getByRole("button", { name: "Gemini 3.5 Flash-Lite" })).toHaveAttribute("aria-pressed", "true");
  await user.click(screen.getByRole("button", { name: "GPT-OSS 20B" }));
  await user.type(screen.getByPlaceholderText(/Busque por ID/), "7A");
  await user.click(await screen.findByText("Synthetic problem"));
  await user.click(screen.getByRole("button", { name: /Categorizar/ }));
  await waitFor(() => expect(api.post).toHaveBeenCalledWith("/ai-lab/problems/7/classify", null, { params: { model_name: "openai/gpt-oss-20b" } }));
  expect(await screen.findByText("Justificativa sintética")).toBeVisible();
  expect(screen.getByText(/Modelo: openai\/gpt-oss-20b/)).toBeVisible();
  expect(screen.queryByText(/Cada classificação faz uma nova chamada/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Produto: ratings/)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Categorizar/ }));
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(2));
  await user.click(screen.getByRole("button", { name: "GPT-OSS 120B" }));
  expect(screen.queryByText("Justificativa sintética")).not.toBeInTheDocument();
});

it("aproveita partes válidas sem fabricar delta para rating inválido", async () => {
  vi.mocked(api.get).mockResolvedValue({ data: [{ id: 7, platform: "CF_OFFICIAL", platform_id: "7A", title: "Synthetic problem" }] });
  vi.mocked(api.post).mockClear();
  vi.mocked(api.post).mockResolvedValue({ data: { rating: null, tags: ["math"], reasoning: "Explicação parcial", real_rating: 1400, real_tags: ["math"], model: "gemini-3.5-flash-lite", rating_status: "out_of_domain", tags_status: "invalid_output", discarded_tags_count: 1 } });
  const user = userEvent.setup();
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><AILab /></QueryClientProvider>);
  await user.type(screen.getByPlaceholderText(/Busque por ID/), "7A");
  await user.click(await screen.findByText("Synthetic problem"));
  await user.click(screen.getByRole("button", { name: /Categorizar/ }));
  expect(await screen.findByText("Resultado parcial")).toBeVisible();
  expect(screen.getByText(/1 tag\(s\) descartada/)).toBeVisible();
  expect(screen.getByText("Explicação parcial")).toBeVisible();
  expect(screen.queryByText("Delta Rating")).not.toBeInTheDocument();
  expect(api.post).toHaveBeenCalledTimes(1);
});

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
