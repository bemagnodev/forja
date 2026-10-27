import { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layouts/PageLayout";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProblemStatusSelect } from "@/components/contests/ProblemStatusSelect";
import { ProblemActionsCell } from "@/components/contests/ProblemActionsCell";
import { CompactProblemTags } from '@/components/contests/CompactProblemTags';
import { ContestIdentity } from '@/components/contests/ContestIdentity';
import { ContestResultCell } from "@/components/contests/ContestResultCell";
import { AlertCircle, ArrowLeft, ExternalLink, Sparkles, Search, CalendarDays, Clock3 } from "lucide-react";
import type { ContestProblem } from "@/components/contests/types";
import type { ContestParticipation } from "@/components/contests/ContestCard";
import { getRatingColor } from "@/lib/ratings";
import { hasNativeRating } from "@/lib/product-classification";

type Filter = "all" | "live" | "upsolved" | "pending" | "unattempted";
const FILTERS: { key: Filter; label: string }[] = [
  { key: "all", label: "Todas" }, { key: "live", label: "No contest" },
  { key: "upsolved", label: "Upsolvadas" }, { key: "pending", label: "A estudar" },
  { key: "unattempted", label: "Não tentadas" },
];
function matches(p: ContestProblem, filter: Filter) {
  if (filter === "live") return p.contest_result?.accepted ?? p.system_status === "SOLVED_LIVE";
  if (filter === "upsolved") return p.contest_result?.is_upsolved ?? p.system_status === "UPSOLVED";
  if (filter === "pending") return p.system_status === "PENDING_UPSOLVE" || p.review_status === "DOABLE";
  if (filter === "unattempted") return p.system_status === "UNATTEMPTED";
  return true;
}
const inputClass = "rounded-lg border border-white/10 bg-zinc-900/60 px-3 py-2.5 text-xs text-white/75 outline-none focus-visible:ring-2 focus-visible:ring-forja";

export function ContestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const contestId = Number(id);
  const validId = Number.isInteger(contestId) && contestId > 0;
  useEffect(() => {
    const main = document.querySelector('main');
    if (main) main.scrollTop = 0;
  }, [contestId]);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("index");
  const [selected, setSelected] = useState<{ id: number; request: number } | null>(null);
  useEffect(() => {
    if (selected) document.getElementById(`questao-${selected.id}`)?.scrollIntoView?.({ behavior: "smooth", block: "center", inline: "nearest" });
  }, [selected]);
  const detailQuery = useQuery({
    queryKey: ["contest", contestId],
    queryFn: async () => (await api.get<ContestParticipation>(`/contests/${contestId}`)).data,
    enabled: validId, retry: false,
  });
  const problemsQuery = useQuery<ContestProblem[]>({
    queryKey: ["contest-problems", contestId],
    queryFn: async () => (await api.get(`/contests/${contestId}/problems`)).data,
    enabled: validId, retry: false,
  });
  const detail = detailQuery.data ?? (!detailQuery.isError ? location.state as ContestParticipation | null : null);
  const problems = problemsQuery.data ?? [];
  const filtered = problems.filter(p => matches(p, filter) && `${p.index} ${p.title}`.toLocaleLowerCase().includes(search.toLocaleLowerCase()))
    .sort((a, b) => {
      if (sort === "rating") return (a.rating ?? a.ai_rating ?? Infinity) - (b.rating ?? b.ai_rating ?? Infinity);
      if (sort === "time") return (a.contest_result?.first_ac_seconds ?? Infinity) - (b.contest_result?.first_ac_seconds ?? Infinity);
      if (sort === "errors") return (b.contest_result?.failed_attempts ?? -1) - (a.contest_result?.failed_attempts ?? -1);
      return a.index.localeCompare(b.index, "en", { numeric: true });
    });
  const partial = problems.some(p => p.contest_result?.coverage !== "complete");
  const verdicts: Record<string, number> = {};
  for (const p of problems) {
    for (const group of [p.contest_result?.errors_before_ac, p.contest_result?.errors_after_ac]) {
      for (const [verdict, count] of Object.entries(group ?? {})) verdicts[verdict] = (verdicts[verdict] ?? 0) + count;
    }
  }
  const errors = Object.values(verdicts).reduce((a, b) => a + b, 0);
  const loading = detailQuery.isPending || problemsQuery.isPending;
  const failed = !validId || detailQuery.isError || problemsQuery.isError;
  const rankKnown = !!detail?.rank_context && detail.rank != null;
  const metrics = [
    { label: "ACs na prova", value: `${detail?.progress?.solved_live ?? 0} / ${detail?.progress?.total ?? problems.length}`, color: "text-emerald-400" },
    { label: "Upsolving", value: String(detail?.progress?.upsolved ?? 0), color: "text-sky-400" },
    { label: rankKnown ? `Ranking ${detail?.rank_context === "VIRTUAL" ? "virtual" : "oficial"}` : "Ranking", value: rankKnown ? `#${detail?.rank}` : "—", color: "text-amber-300" },
    { label: "Erros na prova", value: partial ? (errors ? `≥ ${errors}` : "—") : String(errors), color: "text-white/90" },
  ];
  const goToProblem = (pid: number) => {
    setFilter("all"); setSearch(""); setSelected(current => ({ id: pid, request: (current?.request ?? 0) + 1 }));
  };

  return <PageLayout topbarTitle="Contests"
    title={<span className="break-words text-[clamp(1.25rem,2vw,1.875rem)] leading-tight">{detail?.contest_name || "Detalhe do Contest"}</span>}
    action={<button onClick={() => navigate("/contests")} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-white/70 hover:bg-white/5"><ArrowLeft className="size-3.5" />Voltar</button>}>
    {failed ? <div role="alert" className="rounded-xl border border-red-400/20 bg-red-400/5 p-5 text-sm text-red-300">
      <p className="flex items-center gap-2 font-semibold"><AlertCircle className="size-4" />Não foi possível carregar o contest</p>
      <button className="mt-3 underline" onClick={() => { detailQuery.refetch(); problemsQuery.refetch(); }}>Tentar novamente</button>
    </div> : loading ? <p className="py-20 text-center text-sm text-white/60">Carregando problemas...</p> : <>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-zinc-900/40 px-4 py-4 sm:px-5">
        <div className="space-y-3">
          <ContestIdentity platform={detail?.contest_platform ?? ''} virtual={!!detail?.is_virtual} />
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] text-zinc-500">
            {detail?.participation_date && <span className="inline-flex items-center gap-1.5"><CalendarDays className="size-3.5" />{new Date(detail.participation_date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })}</span>}
            {!!detail?.duration_seconds && <span className="inline-flex items-center gap-1.5"><Clock3 className="size-3.5" />{Math.floor(detail.duration_seconds / 60)} min</span>}
            {rankKnown && detail?.penalty != null && <span>Penalidade <strong className="ml-1 font-medium tabular-nums text-zinc-300">{detail.penalty}</strong></span>}
          </div>
        </div>
        {detail?.url && <div className="flex items-center gap-2">
          <a href={detail.url} target="_blank" rel="noopener noreferrer" title="Abrir contest na plataforma" className="inline-flex items-center gap-2 rounded-lg border border-forja/25 bg-forja/[0.06] px-3 py-2 text-[11px] font-medium text-red-300 transition-colors hover:border-forja/50 hover:bg-forja/10">Abrir contest<ExternalLink className="size-3" /></a>
          <a href={`${detail.url}/standings`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-zinc-800 px-3 py-2 text-[11px] text-zinc-400 hover:border-forja/30 hover:text-zinc-200">Placar<ExternalLink className="size-3" /></a>
        </div>}
      </div>
      <div className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4">
        {metrics.map(m => <div key={m.label} className="rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-4 transition-colors hover:border-forja/25">
          <p className="mb-2 text-[11px] font-medium text-white/55">{m.label}</p><p className={`text-2xl font-bold tabular-nums ${m.color}`}>{m.value}</p>
        </div>)}
      </div>
      <div className="mb-5 flex flex-wrap gap-2 text-[11px] text-white/65">
        {Object.entries(verdicts).map(([key, value]) => <span key={key} className="rounded-md border border-white/10 px-2 py-1">{key} <strong className="ml-1 text-white/85">{value}</strong></span>)}
        {partial && <span className="text-zinc-500">Histórico parcial · Alguns horários e tentativas ainda não puderam ser confirmados</span>}
      </div>
      <section aria-label="Placar por questão" className="mb-6 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.07] px-4 py-3 text-[11px]">
          <span className="border-l-2 border-forja pl-2 font-semibold text-zinc-300">Resultado da prova</span>
        </div>
        <div className="flex overflow-x-auto">
          {[...problems].sort((a, b) => a.index.localeCompare(b.index, "en", { numeric: true })).map(p => <div key={p.id} className="flex min-w-20 flex-1 flex-col items-center border-r border-white/[0.05] py-2 last:border-0">
            <button aria-label={`Ir para questão ${p.index}`} onClick={() => goToProblem(p.id)} className="mb-1 rounded px-3 py-1 text-xs font-bold text-white/65 hover:text-red-300 focus-visible:outline focus-visible:outline-forja">{p.index}</button>
            <ContestResultCell result={p.contest_result} systemStatus={p.system_status} label={p.index} />
          </div>)}
          {!problems.length && <p className="p-5 text-sm text-white/50">Nenhuma questão disponível.</p>}
        </div>
      </section>
      <div className="mb-4 flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">{FILTERS.map(f => <button key={f.key} aria-pressed={filter === f.key} onClick={() => setFilter(f.key)} className={`rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${filter === f.key ? "border-forja/40 bg-forja/10 text-red-300" : "border-white/10 text-white/55 hover:bg-white/5"}`}>
          {f.label} <span className="ml-1.5 opacity-60">{problems.filter(p => matches(p, f.key)).length}</span>
        </button>)}</div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="relative flex-1"><Search className="absolute left-3 top-3 size-3.5 text-white/35" /><input type="search" aria-label="Buscar questão" placeholder="Buscar questão..." value={search} onChange={e => setSearch(e.target.value)} className={`${inputClass} w-full min-w-40 pl-9`} /></label>
          <select aria-label="Ordenar questões" value={sort} onChange={e => setSort(e.target.value)} className={inputClass}>
            <option value="index">Ordem da prova</option><option value="rating">Menor rating</option><option value="time">Momento do AC</option><option value="errors">Mais erros</option>
          </select>
        </div>
      </div>
      <div className="overflow-hidden rounded-xl border border-white/[0.09] bg-[#0c0d11]">
        <Table>
          <TableHeader><TableRow className="bg-white/[0.025] hover:bg-white/[0.025]">
            {["Questão", "Resultado", "Rating / tags", "Triagem", "Ações"].map(h => <TableHead key={h} className="px-4 py-4 text-[11px] font-semibold text-white/55">{h}</TableHead>)}
          </TableRow></TableHeader>
          <TableBody>
            {filtered.map(p => <TableRow key={p.id} id={`questao-${p.id}`} className={`group/row border-white/[0.05] transition-colors ${selected?.id === p.id ? "bg-forja/[0.045]" : "hover:bg-white/[0.025]"}`}>
              <TableCell className="w-[32%] min-w-44 max-w-80 whitespace-normal px-4 py-2.5"><div className="flex items-start gap-3">
                <span className="pt-0.5 text-xs font-bold text-white/35">{p.index}</span>
                {p.url ? <a href={p.url} target="_blank" rel="noopener noreferrer" className="text-[13px] font-medium leading-relaxed text-white/85 hover:text-red-300">{p.title}</a> : <span className="text-[13px] text-white/85">{p.title}</span>}
              </div></TableCell>
              <TableCell className="px-3 py-2"><ContestResultCell result={p.contest_result} systemStatus={p.system_status} label={p.index} /></TableCell>
              <TableCell className="min-w-52 max-w-80 px-4 py-2">
                <div className="flex items-center gap-3"><div className="flex shrink-0 items-center gap-1.5 text-xs font-bold tabular-nums" style={{ color: getRatingColor(p.rating ?? p.ai_rating ?? null) }}>
                  {!hasNativeRating(p.rating) && p.ai_rating != null && <Sparkles className="size-3 text-fuchsia-400" aria-label="Rating estimado por IA" />}
                  {p.rating ?? p.ai_rating ?? "—"}
                </div>
                <CompactProblemTags tags={p.tags?.length ? p.tags : p.ai_tags ?? []} /></div>
              </TableCell>
              <TableCell className="px-3 py-2"><ProblemStatusSelect problemId={p.id} trackingId={p.tracking_id} currentStatus={p.review_status} contestId={contestId} /></TableCell>
              <TableCell className="px-4 py-2"><ProblemActionsCell problem={p} /></TableCell>
            </TableRow>)}
            {!filtered.length && <TableRow><TableCell colSpan={5} className="py-12 text-center text-sm text-white/50">Nenhuma questão neste filtro.</TableCell></TableRow>}
          </TableBody>
        </Table>
      </div>
    </>}
  </PageLayout>;
}
