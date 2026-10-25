import { useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layouts/PageLayout";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ProblemStatusSelect } from "@/components/contests/ProblemStatusSelect";
import { ProblemActionsCell } from "@/components/contests/ProblemActionsCell";
import { AlertCircle, ArrowLeft, ExternalLink, Trophy, CheckCircle, Sparkles } from "lucide-react";
import type { ContestProblem } from "@/components/contests/types";
import { getRatingColor } from "@/lib/ratings";
import { hasNativeRating } from "@/lib/product-classification";

// Cores de rating do Codeforces (usando as CSS vars do design system)
function RatingBadge({ rating, isAi = false }: { rating: number | null; isAi?: boolean }) {
  if (rating == null) return <span className="text-white/20 text-[12px]">—</span>;

  const colorStyle = { color: getRatingColor(rating) };

  return (
    <div className="flex items-center justify-center gap-1.5" title={isAi ? "Rating estimado por IA" : undefined}>
      {isAi && <Sparkles className="w-3 h-3 text-fuchsia-400 opacity-80" />}
      <span 
        className="text-[12px] font-bold tabular-nums"
        style={colorStyle}
      >
        {rating}
      </span>
    </div>
  );
}

type FilterType = "all" | "pending" | "solved" | "unattempted";

const FILTER_LABELS: { key: FilterType; label: string }[] = [
  { key: "all",         label: "Todas" },
  { key: "pending",     label: "Pendentes" },
  { key: "solved",      label: "Resolvidas" },
  { key: "unattempted", label: "Não tentadas" },
];

export function ContestDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const contestId = Number(id);
  const [filter, setFilter] = useState<FilterType>("all");
  
  const { contest_name, url, rank, progress } = location.state || {};
  
  const solve_count = progress?.solved_live || 0;
  const upsolve_count = progress?.upsolved || 0;
  const total_problems = progress?.total || 0;

  const { data: problems = [], isLoading, isError } = useQuery<ContestProblem[]>({
    queryKey: ["contest-problems", contestId],
    queryFn: async () => {
      const { data } = await api.get(`/contests/${contestId}/problems`);
      return data;
    },
    enabled: !!contestId,
  });

  // Filtro local — sem nova requisição ao backend
  const filtered = problems.filter((p) => {
    if (filter === "pending")     return p.system_status === "PENDING_UPSOLVE";
    if (filter === "solved")      return ["SOLVED_LIVE", "UPSOLVED", "PRACTICE_AC"].includes(p.system_status);
    if (filter === "unattempted") return p.system_status === "UNATTEMPTED";
    return true;
  });

  return (
    <PageLayout
      topbarTitle="Contests"
      title={
        <div className="flex items-center gap-3">
          <span className="text-white/90">{contest_name || "Detalhe do Contest"}</span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-white/20 hover:text-[#dc143c] transition-all flex items-center justify-center p-1.5 rounded-lg hover:bg-[#dc143c]/10 border border-transparent hover:border-[#dc143c]/20"
              title="Abrir contest na plataforma"
            >
              <ExternalLink className="w-5 h-5" />
            </a>
          )}
        </div>
      }
      description="Status de cada questão e ferramentas de triagem."
      action={
        <button
          onClick={() => navigate("/contests")}
          className="flex items-center gap-2 text-[12px] text-white/60 hover:text-white transition-colors bg-white/5 px-3 py-1.5 rounded-lg border border-white/10 hover:border-white/20"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Voltar
        </button>
      }
    >
      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-32">
          <div className="flex flex-col items-center gap-4">
            <div className="w-6 h-6 rounded-full border-2 border-[#dc143c] border-t-transparent animate-spin" />
            <span className="text-[11px] text-white/25 font-medium tracking-widest uppercase">
              Carregando problemas...
            </span>
          </div>
        </div>
      )}

      {/* Erro */}
      {isError && (
        <div className="rounded-2xl border flex items-center gap-4 border-red-500/20 bg-red-500/[0.04] p-5 text-red-400">
          <div className="w-8 h-8 rounded-full bg-red-500/10 border border-red-500/15 flex items-center justify-center shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <p className="font-bold text-[14px]">Erro ao carregar problemas</p>
            <p className="text-[12px] opacity-60 mt-0.5">Verifique se o Django está rodando.</p>
          </div>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* Top Stats Scorecards */}
          {(total_problems > 0 || rank !== undefined) && (
            <div className="flex flex-wrap gap-4 mb-8">
              {rank !== undefined && rank !== null && (
                <div className="flex items-center gap-3 bg-white/[0.02] border border-white/[0.05] rounded-xl px-5 py-4 backdrop-blur-sm shadow-lg shadow-black/20">
                  <div className="p-2.5 bg-yellow-500/10 rounded-lg text-yellow-500 border border-yellow-500/20">
                    <Trophy className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold tracking-wider uppercase text-white/30 mb-0.5">Ranking Final</span>
                    <span className="text-xl font-bold text-white/90">#{rank}</span>
                  </div>
                </div>
              )}
              {total_problems !== undefined && total_problems > 0 && (
                <div className="flex items-center gap-3 bg-white/[0.02] border border-white/[0.05] rounded-xl px-5 py-4 backdrop-blur-sm shadow-lg shadow-black/20">
                  <div className="p-2.5 bg-emerald-500/10 rounded-lg text-emerald-400 border border-emerald-500/20">
                    <CheckCircle className="w-5 h-5" />
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[11px] font-bold tracking-wider uppercase text-white/30 mb-0.5">Problemas Resolvidos</span>
                    <div className="flex items-baseline gap-1.5">
                      <span className="text-xl font-bold text-white/90">{solve_count + upsolve_count}</span>
                      <span className="text-[13px] font-medium text-white/40">/ {total_problems}</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Filtros pill */}
          <div className="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-hide">
            {FILTER_LABELS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setFilter(key)}
                className={[
                  "px-4 py-1.5 rounded-full text-[12px] font-semibold border transition-all whitespace-nowrap",
                  filter === key
                    ? "bg-[#dc143c]/20 border-[#dc143c] text-[#dc143c] shadow-[0_0_20px_rgba(220,20,60,0.15)]"
                    : "bg-white/[0.02] border-white/10 text-white/50 hover:bg-white/[0.06] hover:text-white/90",
                ].join(" ")}
              >
                {label}
                {key !== "all" && (
                  <span className="ml-1.5 opacity-60">
                    {key === "pending"     ? problems.filter(p => p.system_status === "PENDING_UPSOLVE").length
                    : key === "solved"     ? problems.filter(p => ["SOLVED_LIVE","UPSOLVED","PRACTICE_AC"].includes(p.system_status)).length
                    : problems.filter(p => p.system_status === "UNATTEMPTED").length}
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Tabela de problemas */}
          <div className="border border-white/[0.07] rounded-2xl overflow-hidden bg-[#0a0a0a]/80 backdrop-blur-2xl shadow-2xl shadow-black/50">
            <Table>
              <colgroup>
                <col style={{ width: "52px" }} />
                <col style={{ width: "30%" }} />
                <col style={{ width: "80px" }} />
                <col />
                <col style={{ width: "150px" }} />
                <col style={{ width: "110px" }} />
              </colgroup>

              <TableHeader>
                <TableRow className="border-b border-white/[0.08] bg-white/[0.02] hover:bg-white/[0.02]">
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 pl-6">#</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 px-3">Problema</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 px-3 text-center">Rating</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 px-3">Tags</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 px-3">Status</TableHead>
                  <TableHead className="text-[10px] uppercase tracking-[0.15em] text-white/40 font-bold py-4 px-3 text-right pr-6">Ações</TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {filtered.length === 0 && (
                  <TableRow className="hover:bg-transparent border-0">
                    <TableCell colSpan={6} className="py-24 text-center">
                      <div className="flex flex-col items-center opacity-20">
                        <AlertCircle className="w-8 h-8 mb-2" />
                        <p className="text-[13px] font-medium">Nenhum problema encontrado</p>
                      </div>
                    </TableCell>
                  </TableRow>
                )}

                {filtered.map((prob) => (
                  <TableRow key={prob.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-all duration-200 group/row">
                    {/* Index */}
                    <TableCell className="pl-6 py-4">
                      <span className="text-[13px] font-bold text-white/20 group-hover/row:text-white/40 transition-colors">{prob.index}</span>
                    </TableCell>

                    {/* Título */}
                    <TableCell className="px-3 py-4">
                      <div className="flex items-center gap-2.5">
                        {prob.url ? (
                          <a 
                            href={prob.url} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-[14px] font-semibold text-white/80 hover:text-[#dc143c] transition-colors inline-flex items-center gap-2 group/link"
                          >
                            <span className="line-clamp-1">{prob.title}</span>
                            <ExternalLink className="w-3.5 h-3.5 opacity-0 -translate-x-1 group-hover/link:opacity-100 group-hover/link:translate-x-0 transition-all text-[#dc143c]" />
                          </a>
                        ) : (
                          <span className="text-[14px] font-semibold text-white/80 line-clamp-1">{prob.title}</span>
                        )}
                        {["SOLVED_LIVE", "UPSOLVED", "PRACTICE_AC"].includes(prob.system_status) && (
                          <div 
                            className="shrink-0 flex items-center justify-center px-1.5 py-0.5 rounded-sm bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.15)]"
                            title="Resolvido"
                          >
                            <span className="text-emerald-500 text-[9px] font-black tracking-widest leading-none mt-[1px]">AC</span>
                          </div>
                        )}
                      </div>
                    </TableCell>

                    {/* Rating */}
                    <TableCell className="px-3 py-4 text-center">
                      <RatingBadge 
                        rating={prob.rating ?? prob.ai_rating}
                        isAi={!hasNativeRating(prob.rating) && prob.ai_rating != null}
                      />
                    </TableCell>

                    {/* Tags */}
                    <TableCell className="px-3 py-4">
                      <div className="flex flex-wrap gap-1.5 items-center">
                        {!hasNativeRating(prob.rating) && prob.ai_tags?.length > 0 && (
                          <Sparkles className="w-3 h-3 text-fuchsia-400 mr-0.5 opacity-80" role="img" aria-label="Tags estimadas por IA" />
                        )}
                        {(prob.tags?.length > 0 ? prob.tags : prob.ai_tags || [])?.slice(0, 3).map((tag) => (
                          <span key={tag} className={`text-[10px] font-bold px-2.5 py-0.5 rounded-md border transition-all ${
                            !prob.tags?.length && prob.ai_tags?.length > 0 
                            ? "bg-fuchsia-500/10 border-fuchsia-500/20 text-fuchsia-300"
                            : "bg-white/[0.03] border-white/[0.08] text-white/40 group-hover/row:border-white/15 group-hover/row:text-white/60"
                          }`}>
                            {tag}
                          </span>
                        ))}
                        {(prob.tags?.length > 0 ? prob.tags : prob.ai_tags || [])?.length > 3 && (
                          <span className="text-[10px] font-bold text-white/15 ml-1">
                            +{(prob.tags?.length > 0 ? prob.tags : prob.ai_tags || []).length - 3}
                          </span>
                        )}
                      </div>
                    </TableCell>

                    {/* Status inline */}
                    <TableCell className="px-3 py-4">
                      <ProblemStatusSelect
                        problemId={prob.id}
                        trackingId={prob.tracking_id}
                        currentStatus={prob.review_status}
                        contestId={contestId}
                      />
                    </TableCell>

                    {/* Ações */}
                    <TableCell className="pr-6 py-4">
                      <ProblemActionsCell problem={prob} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </>
      )}
    </PageLayout>
  );
}
