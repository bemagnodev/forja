import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Sparkles, X, AlertCircle, Clock, Tag } from "lucide-react";
import { PageLayout } from "@/components/layouts/PageLayout";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { PlatformIcon } from "@/components/queue/PlatformIcon";
import { AxiosError } from "axios";
import { BenchmarkResults } from "@/components/ai-lab/BenchmarkResults";
import { ReferenceComparison } from '@/components/ai-lab/ReferenceComparison';
import { AIVisualWarning } from "@/components/ai-lab/AIVisualWarning";
import { ClassificationError } from "@/components/ai-lab/ClassificationError";
import { visualPreview } from '@/lib/visual-preview';

// Tipagens locais
interface ProblemSearchItem {
  id: number;
  platform_id: string;
  title: string;
  platform: string;
}

interface AIPredictionResult {
  rating: number | null;
  tags: string[];
  reasoning: string;
  raw_data: Record<string, unknown> | null;
  real_rating: number | null;
  real_tags: string[];
  model: string | null;
  rating_status: string;
  tags_status: string;
  discarded_tags_count: number;
  visual_status?: string | null;
}

const SUPPORTED_MODELS = [
  { value: "gemini-3.5-flash-lite", label: "Gemini 3.5 Flash-Lite" },
  { value: "openai/gpt-oss-120b", label: "GPT-OSS 120B" },
  { value: "openai/gpt-oss-20b", label: "GPT-OSS 20B" },
];

export function AILab() {
  const [tab, setTab] = useState<"benchmark" | "explore">("explore");
  const [platform, setPlatform] = useState<string>("CODEFORCES");
  const [model, setModel] = useState<string>("gemini-3.5-flash-lite");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProblem, setSelectedProblem] = useState<ProblemSearchItem | null>(null);
  const [responseTime, setResponseTime] = useState<number | null>(null);
  const [previewScenario, setPreviewScenario] = useState('success');

  // Busca
  const { data: searchResults = [] } = useQuery<ProblemSearchItem[]>({
    queryKey: ["problem-search-lab", searchQuery, platform],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return [];
      const params = new URLSearchParams({ q: searchQuery, limit: "8", platform });
      const { data } = await api.get(`/problems/search?${params}`);
      return data;
    },
    enabled: searchQuery.length >= 2,
  });

  // Mutação para Classificação
  const categorizeMutation = useMutation<AIPredictionResult, AxiosError<{ message?: string; detail?: string }>, { problemId: number; modelName: string }>({
    retry: false,
    mutationFn: async ({ problemId, modelName }) => {
      const start = performance.now();
      const { data } = await api.post(`/ai-lab/problems/${problemId}/classify`, null, {
        params: { model_name: modelName, ...(visualPreview ? { preview_scenario: previewScenario } : {}) }
      });
      setResponseTime(performance.now() - start);
      return data;
    },
  });

  const handleCategorize = () => {
    if (!selectedProblem) return;
    categorizeMutation.mutate({ problemId: selectedProblem.id, modelName: model });
  };

  const selectProblem = (p: ProblemSearchItem) => {
    categorizeMutation.reset(); setResponseTime(null);
    setSelectedProblem(p);
    setSearchQuery("");
  };

  const previewExamples = useQuery<ProblemSearchItem[]>({
    queryKey: ['visual-preview-examples'], enabled: visualPreview,
    queryFn: async () => (await api.get('/problems/search?q=999900&limit=15&platform=CODEFORCES')).data,
  });

  return (
    <PageLayout
      topbarTitle="Sistema"
      title="AI Playground"
      description="Explore estimativas de dificuldade e assuntos e compare os resultados dos modelos."
    >
      <div role="tablist" aria-label="AI Playground" className="mb-6 flex gap-2 border-b border-white/10 pb-3">
        {([['explore', 'Explorar'], ['benchmark', 'Benchmark']] as const).map(([value, label]) =>
          <button key={value} id={`ai-lab-tab-${value}`} role="tab" aria-selected={tab === value}
            aria-controls={`ai-lab-panel-${value}`} tabIndex={tab === value ? 0 : -1}
            onClick={() => setTab(value)} onKeyDown={event => {
              if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
                const next = tab === "benchmark" ? "explore" : "benchmark";
                setTab(next); document.getElementById(`ai-lab-tab-${next}`)?.focus();
              }
            }}
            className={`rounded-lg px-4 py-2 text-sm font-medium ${tab === value ? "bg-forja/10 text-red-300 ring-1 ring-forja/30" : "text-white/60 hover:text-white/80"}`}>
            {label}
          </button>)}
      </div>
      {visualPreview && tab === 'explore' && <label className="mb-4 flex flex-wrap items-center gap-3 text-xs text-amber-200">Simulação local (sem IA)
        <select aria-label="Cenário da prévia" value={previewScenario} onChange={e => { setPreviewScenario(e.target.value); categorizeMutation.reset(); setResponseTime(null); }} className="rounded-lg border border-amber-400/20 bg-zinc-950 px-3 py-2">
          <option value="success">Sucesso</option><option value="exact">Rating exato</option><option value="overestimate">Superestimativa (+200)</option><option value="underestimate">Subestimativa (−200)</option><option value="partial">Resultado parcial</option><option value="visual">Questão com imagens</option><option value="error">Erro do provedor</option>
        </select></label>}
      {visualPreview && tab === 'explore' && <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-zinc-400">
        <span>Exemplos locais:</span>
        {[{ id: '999900D', label: 'Com rating oficial' }, { id: '999900C', label: 'Sem rating oficial' }].map(example => {
          const problem = previewExamples.data?.find(p => p.platform_id === example.id);
          return <button key={example.id} disabled={!problem || categorizeMutation.isPending} onClick={() => { if (problem) { setPlatform('CODEFORCES'); selectProblem(problem); } }} className="rounded-lg border border-zinc-800 px-3 py-2 text-zinc-300 hover:bg-zinc-800/60 disabled:opacity-40">{example.label}</button>;
        })}
        <span className="text-[11px]">Escolha o cenário e clique em Classificar. Nenhuma API de IA é chamada.</span>
      </div>}
      {tab === "benchmark" ? <div id="ai-lab-panel-benchmark" role="tabpanel" aria-labelledby="ai-lab-tab-benchmark" className="max-w-6xl pb-12">
        <BenchmarkResults />
      </div> : <div id="ai-lab-panel-explore" role="tabpanel" aria-labelledby="ai-lab-tab-explore" className="max-w-6xl w-full space-y-8 pb-12">
        {/* Formulário de Configuração */}
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-4 sm:p-5 space-y-4">
          <div className="flex items-center gap-2 pb-4 border-b border-white/[0.06]">
            <Sparkles className="w-5 h-5 text-[#dc143c]" />
            <h2 className="text-[14px] font-bold tracking-wide text-white">Configurar Predição</h2>
          </div>

          <div className="space-y-4">
            {/* Linha 1: Configurações Básicas */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-[11px] uppercase text-white/60 font-bold tracking-widest">Modelo de IA</label>
                <div className="flex gap-2">
                  {SUPPORTED_MODELS.map((m) => (
                    <button
                      key={m.value}
                      aria-pressed={model === m.value}
                      disabled={categorizeMutation.isPending}
                      onClick={() => { setModel(m.value); categorizeMutation.reset(); setResponseTime(null); }}
                      className={[
                        "flex-1 py-2.5 rounded-xl text-[11px] font-bold tracking-wide transition-all duration-200 border text-center",
                        model === m.value
                          ? "bg-forja/15 text-white border-forja/35 "
                          : "bg-white/[0.02] border-white/[0.06] text-white/60 hover:text-white/65 hover:bg-white/[0.06]",
                      ].join(" ")}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[11px] uppercase text-white/60 font-bold tracking-widest">Plataforma</label>
                <div className="flex gap-2">
                  {[
                    { value: "CODEFORCES", label: "Codeforces" },
                    { value: "ATCODER", label: "AtCoder" },
                    { value: "CSES", label: "CSES" },
                  ].map((p) => (
                    <button
                      aria-pressed={platform === p.value}
                      key={p.value}
                      disabled={categorizeMutation.isPending}
                      onClick={() => { setPlatform(p.value); setSelectedProblem(null); setSearchQuery(""); categorizeMutation.reset(); setResponseTime(null); }}
                      className={[
                        "flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 rounded-xl text-[11px] font-semibold border transition-all duration-200",
                        platform === p.value
                          ? "bg-white/[0.1] border-white/20 text-white "
                          : "bg-white/[0.02] border-white/[0.05] text-white/60 hover:text-white/65 hover:bg-white/[0.06]",
                      ].join(" ")}
                    >
                      <PlatformIcon platform={p.value} />
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Linha 2: Busca e Ação */}
            <div className="space-y-2">
              <label className="text-[11px] uppercase text-white/60 font-bold tracking-widest">Problema Alvo</label>
              <div className="flex flex-col md:flex-row gap-4 items-start">
                <div className="relative group w-full">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/50 group-focus-within:text-white/60 transition-colors" />
                  <Input
                    disabled={categorizeMutation.isPending}
                    value={selectedProblem ? `${selectedProblem.platform_id} - ${selectedProblem.title}` : searchQuery}
                    onChange={(e) => { setSearchQuery(e.target.value); setSelectedProblem(null); categorizeMutation.reset(); setResponseTime(null); }}
                    placeholder="Busque por ID ou nome (ex: 1A, Theatre)"
                    className="pl-11 h-10 bg-black/40 border-white/[0.09] text-white placeholder:text-white/18 rounded-xl text-[13px] focus-visible:ring-1 focus-visible:ring-white/20"
                  />
                  {selectedProblem && (
                    <button
                      disabled={categorizeMutation.isPending}
                      onClick={() => { setSelectedProblem(null); setSearchQuery(""); categorizeMutation.reset(); setResponseTime(null); }}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-white/25 hover:text-white/55 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                  {/* Dropdown de Busca */}
                  {searchResults.length > 0 && !selectedProblem && (
                    <div className="absolute z-10 w-full mt-2 border border-white/[0.09] rounded-xl max-h-56 overflow-y-auto bg-[#0a0a0a]/98 shadow-2xl backdrop-blur-md">
                      {searchResults.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => selectProblem(p)}
                          className="w-full px-4 py-3 text-left hover:bg-white/[0.06] transition-colors flex items-center gap-3 border-b border-white/[0.05] last:border-0"
                        >
                          <PlatformIcon platform={p.platform} />
                          <span className="text-white/60 font-mono text-[11px] bg-white/[0.04] px-1.5 py-0.5 rounded shrink-0 border border-white/[0.05]">
                            {p.platform_id}
                          </span>
                          <span className="text-white/80 text-[13px] truncate font-medium">{p.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <Button
                  aria-label="Classificar questão"
                  onClick={handleCategorize}
                  disabled={!selectedProblem || categorizeMutation.isPending}
                  className="h-10 shrink-0 gap-2 rounded-lg border border-forja/40 bg-forja px-4 text-xs font-semibold text-white transition-colors hover:bg-zinc-800 disabled:opacity-40"
                >
                  {categorizeMutation.isPending ? (
                    <>
                      <div className="size-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Classificando...
                    </>
                  ) : (
                    <>
                      <Sparkles className="size-3.5" />
                      Classificar
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Estados de Loading */}
        {categorizeMutation.isPending && (
          <div className="space-y-6 animate-pulse">
            <div className="flex gap-4">
              <Skeleton className="h-24 flex-1 bg-white/[0.03] rounded-2xl" />
              <Skeleton className="h-24 flex-1 bg-white/[0.03] rounded-2xl" />
              <Skeleton className="h-24 flex-1 bg-white/[0.03] rounded-2xl" />
            </div>
            <Skeleton className="h-32 w-full bg-white/[0.03] rounded-2xl" />
            <Skeleton className="h-16 w-full bg-white/[0.03] rounded-xl" />
          </div>
        )}

        {/* Erro de Parsing */}
        {categorizeMutation.isError && (
          <ClassificationError error={categorizeMutation.error} />
        )}

        {/* Resultados */}
        {categorizeMutation.isSuccess && categorizeMutation.data && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <p className="text-xs text-zinc-400">Modelo: {categorizeMutation.data.model} · Resultado experimental, sem gravação no banco</p>
            {(categorizeMutation.data.rating_status !== "valid" || categorizeMutation.data.tags_status !== "valid") &&
              <Alert className="grid-cols-[1rem_minmax(0,1fr)] gap-x-2 rounded-xl border-amber-500/30 bg-amber-500/5 text-amber-200">
                <AlertCircle className="row-span-2 size-4" /><AlertTitle className="col-start-2 row-start-1">Resultado parcial</AlertTitle>
                <AlertDescription className="col-start-2 row-start-2 space-y-1 text-xs">
                  {categorizeMutation.data.rating_status !== "valid" && <p>Rating inválido: o modelo não retornou um múltiplo de 100 entre 800 e 3500.</p>}
                  {categorizeMutation.data.tags_status !== "valid" && <p>{categorizeMutation.data.discarded_tags_count > 0 ? `${categorizeMutation.data.discarded_tags_count} tag(s) descartada(s) por não pertencerem à taxonomia oficial.` : "O formato das tags retornadas é inválido."} As partes válidas foram aproveitadas, sem nova chamada.</p>}
                </AlertDescription>
              </Alert>}
            
            <ReferenceComparison realRating={categorizeMutation.data.real_rating ?? null} predictedRating={categorizeMutation.data.rating}
              ratingStatus={categorizeMutation.data.rating_status} realTags={categorizeMutation.data.real_tags ?? []} />

            {categorizeMutation.data.visual_status === 'unprocessed' && <AIVisualWarning />}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="bg-[#080808] border border-white/[0.06] rounded-2xl p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <Tag className="w-4 h-4 text-white/60" />
                  <span className="text-[11px] font-bold text-white/60 uppercase tracking-widest">{categorizeMutation.data.tags_status === "valid" ? "Tags Sugeridas" : "Tags aproveitáveis"}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {categorizeMutation.data.tags.length > 0 ? categorizeMutation.data.tags.map(tag => (
                    <span key={tag} className="text-[11px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded-md">
                      {tag}
                    </span>
                  )) : <span className="text-[12px] text-white/50">Nenhuma tag válida</span>}
                </div>
              </div>

              <div className="bg-[#080808] border border-white/[0.06] rounded-2xl p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-white/60" />
                  <span className="text-[11px] font-bold text-white/60 uppercase tracking-widest">Tempo de Resposta</span>
                </div>
                <div className="flex items-baseline gap-1.5 text-white">
                  <span className="text-3xl font-bold tracking-tighter">
                    {responseTime ? (responseTime / 1000).toFixed(2) : "--"}
                  </span>
                  <span className="text-[12px] text-white/60 font-medium">segundos</span>
                </div>
              </div>
            </div>

            {/* Reasoning Block */}
            <div className="bg-white/[0.03] border-y border-r border-white/[0.06] border-l-4 border-l-[#dc143c] rounded-r-2xl p-6 relative overflow-hidden">
              <div className="absolute top-4 right-4 text-[10px] font-mono text-white/10 uppercase tracking-widest">
                Justificativa resumida
              </div>
              <h3 className="text-[12px] font-bold text-white/70 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#dc143c]" /> Justificativa gerada
              </h3>
              <div className="text-[13px] text-white/60 leading-relaxed whitespace-pre-wrap font-medium">
                {categorizeMutation.data.reasoning}
              </div>
            </div>

            {/* Accordion Raw Scraper */}
            {categorizeMutation.data.raw_data && (
              <Accordion className="w-full bg-[#080808] border border-white/[0.06] rounded-xl overflow-hidden">
                <AccordionItem value="raw-data" className="border-0">
                  <AccordionTrigger className="px-5 py-4 hover:bg-white/[0.02] hover:no-underline text-[12px] font-bold text-white/60">
                    Dados Brutos do Scraper
                  </AccordionTrigger>
                  <AccordionContent className="border-t border-white/[0.06] bg-black/40">
                    <div className="max-h-96 overflow-y-auto p-4 custom-scrollbar">
                      <pre className="text-[11px] font-mono text-white/50 leading-relaxed">
                        {JSON.stringify(categorizeMutation.data.raw_data, null, 2)}
                      </pre>
                    </div>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            )}
          </div>
        )}
      </div>}
    </PageLayout>
  );
}
