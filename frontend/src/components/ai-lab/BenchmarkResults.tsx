import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PredictionChart } from "./PredictionChart";
import { RatingHeatmap } from "./RatingHeatmap";
import { MetricHelp } from "./MetricHelp";
import { PromptDetails, type PublishedPrompt } from "./PromptDetails";
import { TooltipProvider } from "@/components/ui/tooltip";
import { X, FlaskConical, ChevronDown } from "lucide-react";

interface Prediction {
  rating?: number | null;
  rating_status: string;
  tags?: string[] | null;
  tags_status: string;
  justification?: string;
  error?: string;
}
export interface BenchmarkProblem {
  key: string;
  reference: { rating: number; tags: string[] };
  predictions: Record<string, Prediction>;
}
export interface BenchmarkRun {
  id: string;
  label: string;
  provider: string;
  model: string;
  prompt_version?: string;
  strategy_label?: string;
  generation_attempts: number;
  historical_failures: Record<string, number>;
  metrics: {
    mae: number | null; within_200: number | null; tags_micro_f1: number | null;
    rating_valid: number; rating_coverage: number | null; rating_failure_rate: number | null;
    tags_valid?: number | null; tags_coverage: number | null; tags_failure_rate: number | null;
    rating_failures: Record<string, number>; pending: number; responded: number; latency_median: number | null;
  };
}
export interface RatingBand { label: string; total: number; compared: number; mae: Record<string, number | null> }
interface BenchmarkSummary { id: string; label: string; version: string; split: string }
interface Benchmark extends BenchmarkSummary {
  dataset: { version: string; split: string; total: number; hash: string; seed: number };
  prompt: { hash: string | null };
  prompts?: PublishedPrompt[];
  selection_note?: string;
  bands: RatingBand[];
  intersections: { rating: string[]; tags: string[] };
  runs: BenchmarkRun[];
  problems: BenchmarkProblem[];
}

const number = (value: number | null | undefined, digits = 1) => value == null ? "—" : value.toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
const percent = (value: number | null | undefined) => value == null ? "—" : `${number(value * 100, 0)}%`;
const card = "rounded-xl border border-zinc-800 bg-zinc-900/30 p-5 sm:p-6";
const selectClass = "max-w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-zinc-200 outline-none focus:ring-2 focus:ring-primary";

export function BenchmarkResults() {
  const [selectedId, setSelectedId] = useState("");
  const [modelId, setModelId] = useState("");
  const [keys, setKeys] = useState<string[]>([]);
  const [problemKey, setProblemKey] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const trigger = useRef<HTMLElement | null>(null);
  useEffect(() => { if (keys.length) heading.current?.focus(); }, [keys]);
  const listing = useQuery({ queryKey: ["ai-lab-benchmarks"], queryFn: async () =>
    (await api.get<{ benchmarks: BenchmarkSummary[] }>("/ai-lab/benchmarks")).data.benchmarks });
  const id = selectedId || listing.data?.[0]?.id || "";
  const detail = useQuery({ queryKey: ["ai-lab-benchmark", id], enabled: Boolean(id), queryFn: async () =>
    (await api.get<Benchmark>(`/ai-lab/benchmarks/${encodeURIComponent(id)}`)).data });
  const close = () => { setKeys([]); trigger.current?.focus(); };

  if (listing.isError || detail.isError) return <div role="alert" className={card}>
    <p>Não foi possível carregar os resultados salvos.</p><button className="mt-3 text-primary underline" onClick={() => { if (listing.isError) void listing.refetch(); else void detail.refetch(); }}>Tentar novamente</button>
  </div>;
  if (listing.isPending) return <p role="status" className="text-zinc-400">Carregando benchmarks…</p>;
  if (!listing.data?.length) return <div className={card}><p>Nenhum benchmark salvo disponível.</p><p className="mt-2 text-sm text-zinc-500">Selecione Explorar para usar a classificação individual. Esta aba mostra somente avaliações disponibilizadas.</p></div>;
  const data = detail.data;
  const promptVersions = [...new Set((data?.runs || []).filter(run => run.provider !== "baseline")
    .map(run => run.prompt_version).filter((version): version is string => Boolean(version)))].sort();
  const promptNames: Record<string, string> = { classification_v1: "A (v1)", classification_v2: "B (v2)", classification_v3: "C (v3)" };
  const strategyLabels = promptVersions.map(version => data?.runs.find(run => run.prompt_version === version && run.strategy_label)?.strategy_label);
  const promptLabel = strategyLabels.length && strategyLabels.every(Boolean)
    ? strategyLabels.join(" e ")
    : promptVersions.length
    ? `${promptVersions.length > 1 ? "Prompts" : "Prompt"} ${promptVersions.map(version => promptNames[version] || version).join(" e ")}`
    : "Versão do prompt não informada";
  const runs = [...(data?.runs || [])].sort((a, b) => (a.metrics.mae ?? Infinity) - (b.metrics.mae ?? Infinity) || a.id.localeCompare(b.id));
  const graphRun = runs.find(run => run.id === modelId) || runs.find(run => run.provider !== "baseline") || runs[0];
  const problem = data?.problems.find(p => p.key === problemKey);
  const prediction = problem && graphRun ? problem.predictions[graphRun.id] : null;
  return <TooltipProvider delay={100}><div className="space-y-6 text-zinc-300">
    {data && <header className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-5">
      <div><div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500"><FlaskConical className="size-3.5 text-primary" /> Benchmark de classificação</div>
        <div className="flex flex-wrap items-center gap-3"><h2 className="text-xl font-bold tracking-tight text-zinc-100">{data.label}</h2><span className="rounded-md border border-forja/25 bg-forja/10 px-2.5 py-1 text-xs font-semibold text-red-400">{data.dataset.total} problemas</span></div>
        <p className="mt-2 text-xs text-zinc-500">{data.dataset.split === "development" ? "Desenvolvimento · resultado exploratório" : "Avaliação final"} · {promptLabel}</p>
      </div>
      {listing.data.length > 1 && <label className="flex flex-col gap-1.5 text-xs text-zinc-500">Conjunto de resultados<select className={selectClass} aria-label="Conjunto de resultados" value={id} onChange={event => { setSelectedId(event.target.value); setModelId(""); setKeys([]); }}>{listing.data.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label>}
    </header>}
    {detail.isPending && <p role="status">Carregando comparação…</p>}
    {data && <>
      <details className="text-xs text-zinc-500"><summary className="w-fit cursor-pointer rounded py-1 outline-none focus-visible:ring-2 focus-visible:ring-primary">Sobre o experimento</summary><div className="mt-3 space-y-2 leading-relaxed">
        <p>Problemas do Codeforces entre 800 e 2400. Mesmos enunciados preparados; referência oficial separada da entrada. Configuração: {promptLabel}. O baseline usa a mediana do desenvolvimento e estima apenas rating.</p>
        <p>Qualidade na interseção válida: rating {data.intersections.rating.length}/{data.dataset.total}; tags {data.intersections.tags.length}/{data.dataset.total}. Cobertura considera todos os problemas. A dispersão mostra os resultados válidos de cada modelo.</p>
        <p className="break-all font-mono">Dataset {data.dataset.version} · {data.dataset.hash} · seed {data.dataset.seed} · Prompt {data.prompt.hash || (promptVersions.length > 1 ? "por execução" : "não informado")}</p>
      </div></details>
      {data.selection_note && <p role="note" className="rounded-lg border border-forja/20 bg-forja/5 px-4 py-3 text-xs leading-relaxed text-zinc-400">{data.selection_note}</p>}
      {!data.intersections.rating.length && <p className="text-sm text-orange-300">Nenhum item válido em comum para rating. MAE indisponível.</p>}
      <section className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full min-w-[650px] text-left text-sm"><caption className="sr-only">Comparação de qualidade e cobertura dos modelos</caption>
          <thead className="border-b border-zinc-800 bg-zinc-900/50"><tr><th className="px-5 py-3 text-xs text-zinc-500"><MetricHelp label="Modelo">Configuração avaliada. O baseline é uma referência estatística sem IA.</MetricHelp></th>
            <th className="px-5 py-3"><MetricHelp label="Erro médio">MAE: distância média entre rating estimado e oficial nos itens válidos em comum. Menor é melhor. Estimar 1400 para 1800 gera erro de 400 pontos.</MetricHelp></th>
            <th className="px-5 py-3"><MetricHelp label="Até ±200">Proporção de previsões com erro de até 200 pontos na mesma interseção válida. Maior é melhor.</MetricHelp></th>
            <th className="px-5 py-3"><MetricHelp label="Cobertura">Previsões válidas sobre todos os problemas. Falhas e pendências são apresentadas separadamente; não entram como erro zero.</MetricHelp></th>
            <th className="px-5 py-3"><MetricHelp label="F1 de tags">Qualidade das tags previstas, de 0 a 1; maior é melhor. O F1 micro combina as tags corretas, as extras e as que faltaram, somando os resultados dos problemas válidos em comum. Não representa a porcentagem de problemas totalmente corretos. O baseline não estima tags.</MetricHelp></th></tr></thead>
          <tbody>{runs.map(run => <tr key={run.id} className="border-b border-zinc-800/60 last:border-0 hover:bg-zinc-900/30">
            <th scope="row" className="px-5 py-5 font-medium"><span className="block text-zinc-100">{run.label}</span><span className="text-[11px] font-normal text-zinc-500">{run.provider === "baseline" ? "Referência sem IA" : run.provider}</span></th>
            <td className="min-w-36 px-5 py-4"><span className="font-mono text-zinc-100">{number(run.metrics.mae)}</span><span className="ml-1 text-[10px] text-zinc-600">pontos</span>{run.metrics.mae != null && <div role="meter" aria-label={`Erro médio: ${run.label}`} aria-valuemin={0} aria-valuemax={1000} aria-valuenow={Math.min(run.metrics.mae, 1000)} aria-valuetext={`${run.metrics.mae} pontos${run.metrics.mae > 1000 ? "; acima da escala visual de 1000 pontos" : ""}`} className="mt-2 h-1 rounded bg-zinc-800"><div className={`h-1 rounded ${run.provider === "baseline" ? "bg-zinc-500" : "bg-forja/80"}`} style={{ width: `${Math.min(run.metrics.mae / 1000, 1) * 100}%` }} /></div>}{run.metrics.mae != null && run.metrics.mae > 1000 && <span className="mt-1 block text-[10px] text-zinc-500">Acima da escala</span>}</td>
            <td className="px-5 py-4 font-mono">{percent(run.metrics.within_200)}</td>
            <td className="px-5 py-4"><span>{run.metrics.rating_valid}/{data.dataset.total} ({percent(run.metrics.rating_coverage)})</span>
              {!!Object.keys(run.metrics.rating_failures).length && <span className="mt-1 block text-xs text-orange-300">{Object.values(run.metrics.rating_failures).reduce((a, b) => a + b, 0)} falha(s) · {percent(run.metrics.rating_failure_rate)}</span>}
              {!!run.metrics.pending && <span className="mt-1 block text-xs text-zinc-500">{run.metrics.pending} pendente(s)</span>}</td>
            <td className="px-5 py-4 font-mono">{number(run.metrics.tags_micro_f1, 3)}{run.metrics.tags_valid != null && <span className="mt-1 block font-sans text-[10px] text-zinc-500">Tags válidas: {run.metrics.tags_valid}/{data.dataset.total}</span>}</td>
          </tr>)}</tbody>
        </table><div className="border-t border-zinc-800 px-5 py-3 text-[11px] text-zinc-500"><p>Ordenado pelo menor erro médio · {data.intersections.rating.length} problemas comparados para rating · Escala visual: 0–1.000 pontos</p><p className="mt-1">Tags comparadas em {data.intersections.tags.length}/{data.dataset.total} problemas</p></div>
      </section>
      <section className={card}><h3 className="font-semibold text-zinc-100">Onde cada modelo erra mais</h3><p className="mb-4 mt-1 text-xs text-zinc-500">Erro médio por faixa de rating oficial</p><RatingHeatmap bands={data.bands || []} runs={runs} />
        {data.bands.length > 0 && <p className="mt-4 text-xs text-zinc-500">Amostra: {data.bands.every(band => band.total === data.bands[0].total) ? `${data.bands[0].total} problemas selecionados por faixa` : "quantidades por faixa indicadas nas células"}. Falhas podem reduzir a quantidade comparada.</p>}
      </section>
      {graphRun && <section className={card}><div className="mb-4 flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-semibold text-zinc-100">Rating oficial × estimativa</h3><p className="mt-1 text-xs text-zinc-500">Um modelo por vez · posições preservadas · detalhes ao selecionar</p></div><select className={selectClass} aria-label="Modelo no gráfico" value={graphRun.id} onChange={event => { setModelId(event.target.value); setKeys([]); }}>{runs.map(run => <option key={run.id} value={run.id}>{run.label}</option>)}</select></div>
        <PredictionChart key={graphRun.id} problems={data.problems} run={graphRun} onSelect={group => { trigger.current = document.activeElement as HTMLElement; setKeys(group); setProblemKey(group[0]); }} />
      </section>}
      {keys.length > 0 && problem && graphRun && <section role="complementary" aria-labelledby="problem-heading" onKeyDown={event => { if (event.key === "Escape") close(); }}
        className={`${card} xl:fixed xl:bottom-6 xl:right-6 xl:top-20 xl:z-40 xl:w-[390px] xl:overflow-y-auto xl:bg-zinc-950 xl:shadow-2xl`}>
        <div className="flex items-start justify-between gap-4"><div><p className="mb-2 text-[10px] uppercase tracking-widest text-primary">Detalhe do problema</p><h3 ref={heading} tabIndex={-1} id="problem-heading" className="font-semibold text-zinc-100 outline-none">Problema {problem.key}</h3></div><button onClick={close} aria-label="Fechar detalhe" className="rounded p-1 text-zinc-500 hover:text-white focus-visible:ring-2 focus-visible:ring-primary"><X className="size-4" /></button></div>
        {keys.length > 1 && <label className="mt-4 block text-xs">{keys.length} problemas nesta posição<select className={`${selectClass} mt-2 w-full`} aria-label="Problema do grupo" value={problemKey} onChange={e => setProblemKey(e.target.value)}>{keys.map(key => <option key={key} value={key}>{key}</option>)}</select></label>}
        <p className="mt-5 text-sm text-zinc-500">{graphRun.label}</p><div className="my-4 grid grid-cols-2 gap-3"><div className="rounded-lg bg-zinc-900 p-3 text-xs text-zinc-500">Rating oficial<strong className="mt-2 block text-2xl text-zinc-100">{problem.reference.rating}</strong></div><div className="rounded-lg border border-forja/20 bg-forja/5 p-3 text-xs text-zinc-500">Estimado<strong className="mt-2 block text-2xl text-zinc-100">{prediction?.rating ?? "—"}</strong></div></div>
        <p className="text-sm">Erro: {prediction?.rating != null ? `${Math.abs(prediction.rating - problem.reference.rating)} pontos` : "indisponível"}</p><p className="mt-5 text-xs leading-relaxed text-zinc-500">Tags oficiais: <span className="text-zinc-300">{problem.reference.tags.join(", ")}</span></p><p className="mt-2 text-xs leading-relaxed text-zinc-500">Tags estimadas: <span className="text-zinc-300">{prediction?.tags_status === "valid" ? prediction.tags?.join(", ") : prediction?.tags_status === "not_applicable" ? "não aplicável" : prediction?.tags_status === "pending" ? "pendente" : "saída inválida"}</span></p>
        {prediction?.justification && <div className="mt-6 border-t border-zinc-800 pt-4"><h4 className="mb-2 text-xs font-medium text-zinc-300">Justificativa salva</h4><p className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-400">{prediction.justification}</p></div>}
      </section>}
      {data.prompts?.length ? <PromptDetails key={data.id} prompts={data.prompts} /> : null}
      <details className={card}><summary className="flex cursor-pointer list-none items-center justify-between text-sm text-zinc-400 outline-none focus-visible:ring-2 focus-visible:ring-primary">Detalhes da avaliação<ChevronDown className="size-4" /></summary><div className="mt-5 space-y-4 text-xs leading-relaxed text-zinc-500">
        {runs.map(run => <div key={run.id}><h4 className="font-medium text-zinc-300">{run.label}</h4><p>{run.metrics.responded} respostas · {run.metrics.pending} pendentes · latência mediana: {run.provider === "baseline" ? "não aplicável" : `${number(run.metrics.latency_median, 2)} s`}</p><p>Cobertura tags: {percent(run.metrics.tags_coverage)} · falhas tags: {percent(run.metrics.tags_failure_rate)}</p><p>{run.generation_attempts} tentativas de geração · falhas históricas: {Object.entries(run.historical_failures).map(([name, count]) => `${name}: ${count}`).join(", ") || "nenhuma"}</p></div>)}
        <p>Falhas anteriores permanecem registradas após uma recuperação. Leituras da página não chamam IA. Nos experimentos finais, a latência é o tempo registrado da tentativa de resposta. Não inclui a cadência entre chamadas nem as pausas de retomada; não equivale à duração total do lote. Pilotos antigos podem usar outra política de medição.</p>
      </div></details>
    </>}
  </div></TooltipProvider>;
}
