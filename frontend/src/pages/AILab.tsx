import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { Search, Sparkles, X, AlertCircle, Clock, Tag, Target, CheckCircle2, ChevronRight } from "lucide-react";
import { PageLayout } from "@/components/layouts/PageLayout";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { PlatformIcon } from "@/components/queue/PlatformIcon";
import { getRatingColor } from "@/lib/ratings";
import { AxiosError } from "axios";

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
  raw_data: Record<string, any>;
  real_rating: number | null;
  real_tags: string[];
}

const SUPPORTED_MODELS = [
  { value: "gemini-3.1-flash-lite-preview", label: "Gemini 3.1 Lite" },
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
  { value: "gemini-3-flash-preview", label: "Gemini 3.0 Flash" },
];

export function AILab() {
  const [platform, setPlatform] = useState<string>("CODEFORCES");
  const [model, setModel] = useState<string>("gemini-3.1-flash-lite-preview");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProblem, setSelectedProblem] = useState<ProblemSearchItem | null>(null);
  const [responseTime, setResponseTime] = useState<number | null>(null);

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
  const categorizeMutation = useMutation<AIPredictionResult, AxiosError, { problemId: number; force?: boolean }>({
    mutationFn: async ({ problemId, force = false }) => {
      const start = performance.now();
      const { data } = await api.post(`/problems/${problemId}/predict`, null, {
        params: { model_name: model, force }
      });
      setResponseTime(performance.now() - start);
      return data;
    },
  });

  const handleCategorize = (e: React.MouseEvent) => {
    if (!selectedProblem) return;
    categorizeMutation.mutate({ problemId: selectedProblem.id, force: e.ctrlKey || e.metaKey || e.shiftKey });
  };

  const selectProblem = (p: ProblemSearchItem) => {
    setSelectedProblem(p);
    setSearchQuery("");
  };

  const getDeltaColor = (delta: number) => {
    if (delta <= 100) return "text-emerald-400 bg-emerald-400/10 border-emerald-400/20";
    if (delta <= 200) return "text-amber-400 bg-amber-400/10 border-amber-400/20";
    return "text-red-400 bg-red-400/10 border-red-400/20";
  };

  return (
    <PageLayout
      topbarTitle="Sistema"
      title="AI Playground"
      description="Teste a engine de IA de classificação e avalie acurácia dos modelos."
    >
      <div className="max-w-6xl w-full space-y-8 pb-12">
        {/* Formulário de Configuração */}
        <div className="bg-white/[0.02] border border-white/[0.06] rounded-2xl p-6 space-y-6">
          <div className="flex items-center gap-2 pb-4 border-b border-white/[0.06]">
            <Sparkles className="w-5 h-5 text-[#dc143c]" />
            <h2 className="text-[14px] font-bold tracking-wide text-white">Configurar Predição</h2>
          </div>

          <div className="space-y-6">
            {/* Linha 1: Configurações Básicas */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Modelo de IA</label>
                <div className="flex gap-2">
                  {SUPPORTED_MODELS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setModel(m.value)}
                      className={[
                        "flex-1 py-2.5 rounded-xl text-[11px] font-bold tracking-wide transition-all duration-200 border text-center",
                        model === m.value
                          ? "bg-purple-600/15 text-white border-purple-500/35 shadow-lg shadow-purple-500/10"
                          : "bg-white/[0.02] border-white/[0.06] text-white/35 hover:text-white/65 hover:bg-white/[0.06]",
                      ].join(" ")}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Plataforma</label>
                <div className="flex gap-2">
                  {[
                    { value: "CODEFORCES", label: "Codeforces" },
                    { value: "ATCODER", label: "AtCoder" },
                    { value: "CSES", label: "CSES" },
                  ].map((p) => (
                    <button
                      key={p.value}
                      onClick={() => { setPlatform(p.value); setSelectedProblem(null); setSearchQuery(""); }}
                      className={[
                        "flex-1 flex items-center justify-center gap-1.5 px-2 py-2.5 rounded-xl text-[11px] font-semibold border transition-all duration-200",
                        platform === p.value
                          ? "bg-white/[0.1] border-white/20 text-white shadow-lg shadow-white/5"
                          : "bg-white/[0.02] border-white/[0.05] text-white/35 hover:text-white/65 hover:bg-white/[0.06]",
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
              <label className="text-[10px] uppercase text-white/30 font-bold tracking-widest">Problema Alvo</label>
              <div className="flex flex-col md:flex-row gap-4 items-start">
                <div className="relative group w-full">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-white/20 group-focus-within:text-white/60 transition-colors" />
                  <Input
                    value={selectedProblem ? `${selectedProblem.platform_id} - ${selectedProblem.title}` : searchQuery}
                    onChange={(e) => { setSearchQuery(e.target.value); setSelectedProblem(null); }}
                    placeholder="Busque por ID ou nome (ex: 1A, Theatre)"
                    className="pl-11 h-12 bg-black/40 border-white/[0.09] text-white placeholder:text-white/18 rounded-xl text-[13px] focus-visible:ring-1 focus-visible:ring-white/20"
                  />
                  {selectedProblem && (
                    <button
                      onClick={() => { setSelectedProblem(null); setSearchQuery(""); }}
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
                          <span className="text-white/40 font-mono text-[11px] bg-white/[0.04] px-1.5 py-0.5 rounded shrink-0 border border-white/[0.05]">
                            {p.platform_id}
                          </span>
                          <span className="text-white/80 text-[13px] truncate font-medium">{p.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <Button
                  onClick={handleCategorize}
                  disabled={!selectedProblem || categorizeMutation.isPending}
                  title="Ctrl+Click ou Shift+Click para forçar o recálculo (ignorar cache)"
                  className="bg-[#dc143c] hover:bg-[#dc143c]/90 text-white font-bold h-12 px-8 rounded-xl transition-all duration-200 disabled:opacity-40 text-[13px] border border-[#dc143c]/60 shadow-lg shadow-[#dc143c]/20 w-full md:w-auto shrink-0"
                >
                  {categorizeMutation.isPending ? (
                    <>
                      <div className="w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Classificando...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4 mr-2" />
                      Categorizar
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
          <Alert className="bg-red-500/10 border-red-500/30 text-red-200 rounded-xl">
            <AlertCircle className="h-4 w-4 !text-red-400" />
            <AlertTitle className="text-red-300 font-bold ml-2">Erro ao Processar Problema</AlertTitle>
            <AlertDescription className="ml-2 mt-1 opacity-80 text-[13px]">
              A IA não conseguiu ler este formato. Isso ocorre geralmente em questões antigas (ex: PDF images) ou iframes complexos. 
              {categorizeMutation.error.response?.data?.message && (
                <div className="mt-2 p-2 bg-black/40 rounded border border-red-500/20 font-mono text-[10px]">
                  {categorizeMutation.error.response.data.message}
                </div>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Resultados */}
        {categorizeMutation.isSuccess && categorizeMutation.data && (
          <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            
            {/* Painel de Acurácia */}
            {(categorizeMutation.data.real_rating || categorizeMutation.data.real_tags?.length > 0) && (
              <div className="bg-gradient-to-r from-emerald-500/[0.05] to-transparent border border-emerald-500/10 rounded-2xl p-6 flex flex-col gap-6">
                <div className="flex items-center gap-3 pb-4 border-b border-emerald-500/10">
                  <div className="w-10 h-10 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0 border border-emerald-500/20 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                    <Target className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h3 className="text-emerald-400 font-bold text-[14px]">Análise de Acurácia</h3>
                    <p className="text-emerald-400/60 text-[12px] mt-0.5">
                      Comparação entre predição da IA e os dados oficiais da plataforma
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {categorizeMutation.data.real_rating && (
                    <div className="bg-black/40 rounded-xl border border-white/[0.05] p-4 flex flex-col justify-center">
                      <span className="text-[11px] text-white/30 uppercase tracking-widest font-bold mb-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500/50"></span> Delta Rating
                      </span>
                      {categorizeMutation.data.rating === categorizeMutation.data.real_rating ? (
                        <div className="flex items-center justify-center gap-2 text-emerald-400 bg-emerald-400/10 px-3 py-2 rounded-lg text-[13px] font-bold border border-emerald-400/20">
                          <CheckCircle2 className="w-4 h-4" /> Match Perfeito
                        </div>
                      ) : (
                        <div className="flex items-center justify-center gap-4 bg-white/[0.02] py-2 rounded-lg border border-white/[0.02]">
                          <div className="text-center">
                            <div className="text-[10px] text-white/30 uppercase mb-0.5">Oficial</div>
                            <span 
                              className="text-[15px] font-mono font-bold"
                              style={{ color: getRatingColor(categorizeMutation.data.real_rating) }}
                            >
                              {categorizeMutation.data.real_rating}
                            </span>
                          </div>
                          <ChevronRight className="w-4 h-4 text-white/20" />
                          <div className="text-center">
                            <div className="text-[10px] text-white/30 uppercase mb-0.5">IA</div>
                            <span 
                              className="text-[15px] font-mono font-bold"
                              style={{ color: getRatingColor(categorizeMutation.data.rating) }}
                            >
                              {categorizeMutation.data.rating || 'N/A'}
                            </span>
                          </div>
                          <div className="h-8 w-[1px] bg-white/[0.1] mx-2"></div>
                          <span className={`text-[14px] px-2.5 py-1 rounded-md font-bold border ${getDeltaColor(Math.abs((categorizeMutation.data.rating || 0) - categorizeMutation.data.real_rating))}`}>
                            Δ {Math.abs((categorizeMutation.data.rating || 0) - categorizeMutation.data.real_rating)}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {categorizeMutation.data.real_tags?.length > 0 && (
                    <div className="bg-black/40 rounded-xl border border-white/[0.05] p-4 flex flex-col md:col-span-2">
                      <span className="text-[11px] text-white/30 uppercase tracking-widest font-bold mb-3 flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500/50"></span> Tags Oficiais
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {categorizeMutation.data.real_tags.map(tag => (
                          <span key={tag} className="text-[11px] bg-blue-500/10 text-blue-300 px-2.5 py-1 rounded-md border border-blue-500/20 whitespace-nowrap">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-[#080808] border border-white/[0.06] rounded-2xl p-5 flex flex-col relative overflow-hidden group">
                <div className="absolute top-0 right-0 w-32 h-32 bg-[#dc143c]/5 rounded-full blur-3xl -mr-10 -mt-10 transition-opacity group-hover:opacity-100 opacity-50" />
                <div className="flex items-center gap-2 mb-3">
                  <Target className="w-4 h-4 text-white/40" />
                  <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest">Rating Previsto</span>
                </div>
                <div 
                  className="text-3xl font-bold tracking-tighter"
                  style={{ color: getRatingColor(categorizeMutation.data.rating) }}
                >
                  {categorizeMutation.data.rating ?? <span className="text-white/20">N/A</span>}
                </div>
              </div>

              <div className="bg-[#080808] border border-white/[0.06] rounded-2xl p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <Tag className="w-4 h-4 text-white/40" />
                  <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest">Tags Sugeridas</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {categorizeMutation.data.tags.length > 0 ? categorizeMutation.data.tags.map(tag => (
                    <span key={tag} className="text-[11px] font-medium bg-purple-500/10 text-purple-300 border border-purple-500/20 px-2 py-0.5 rounded-md">
                      {tag}
                    </span>
                  )) : <span className="text-[12px] text-white/20">Nenhuma tag inferida</span>}
                </div>
              </div>

              <div className="bg-[#080808] border border-white/[0.06] rounded-2xl p-5 flex flex-col">
                <div className="flex items-center gap-2 mb-3">
                  <Clock className="w-4 h-4 text-white/40" />
                  <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest">Tempo de Resposta</span>
                </div>
                <div className="flex items-baseline gap-1.5 text-white">
                  <span className="text-3xl font-bold tracking-tighter">
                    {responseTime ? (responseTime / 1000).toFixed(2) : "--"}
                  </span>
                  <span className="text-[12px] text-white/30 font-medium">segundos</span>
                </div>
              </div>
            </div>

            {/* Reasoning Block */}
            <div className="bg-white/[0.03] border-y border-r border-white/[0.06] border-l-4 border-l-[#dc143c] rounded-r-2xl p-6 relative overflow-hidden">
              <div className="absolute top-4 right-4 text-[10px] font-mono text-white/10 uppercase tracking-widest">
                Chain of Thought
              </div>
              <h3 className="text-[12px] font-bold text-white/70 uppercase tracking-widest mb-4 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#dc143c]" /> Raciocínio da IA
              </h3>
              <div className="text-[13px] text-white/60 leading-relaxed whitespace-pre-wrap font-medium">
                {categorizeMutation.data.reasoning}
              </div>
            </div>

            {/* Accordion Raw Scraper */}
            {categorizeMutation.data.raw_data && (
              <Accordion type="single" collapsible className="w-full bg-[#080808] border border-white/[0.06] rounded-xl overflow-hidden">
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
      </div>
    </PageLayout>
  );
}
