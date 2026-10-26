import { Link } from "react-router-dom";
import { ContestProgressBar } from "./ContestProgressBar";
import { Trophy, ArrowUpRight } from "lucide-react";

export interface ContestProgress {
  solved_live: number;
  pending_upsolve: number;
  upsolved: number;
  unattempted: number;
  total: number;
}

export interface ContestParticipation {
  id: number;
  contest_id: number;
  contest_name: string;
  contest_platform: string;
  participation_date: string | null;
  is_virtual: boolean;
  has_debt: boolean;
  progress: ContestProgress;
  url: string | null;
  rank: number | null;
  solve_count: number;
  upsolve_count: number;
  total_problems: number;
  rank_context?: string;
  penalty?: number | null;
  session_start_time?: string | null;
  duration_seconds?: number | null;
}

const PLATFORM_BADGE: Record<string, { label: string; cls: string }> = {
  CF_OFFICIAL: { label: "Codeforces",  cls: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  CF_GYM:      { label: "CF Gym",      cls: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  ATCODER:     { label: "AtCoder",     cls: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
};

export function ContestCard({ participation, onNavigate }: { participation: ContestParticipation; onNavigate?: () => void }) {
  const { 
    contest_id, contest_name, contest_platform, participation_date, 
    is_virtual, progress, url, rank
  } = participation;

  const badge = PLATFORM_BADGE[contest_platform] ?? { label: contest_platform, cls: "bg-white/5 text-white/40 border-white/10" };

  const formattedDate = participation_date
    ? new Date(participation_date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
    : null;

  return (
    <Link to={`/contests/${contest_id}`} state={{ contest_name, url, rank, progress }} onClick={onNavigate}
      className="group flex min-h-[210px] flex-col rounded-2xl border border-white/[0.09] bg-[#101116] p-5 text-left transition-colors hover:border-white/20 hover:bg-[#14151c] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-red-400">
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className={`rounded-md border px-2 py-0.5 text-[10px] font-semibold ${badge.cls}`}>{contest_platform === "CF_GYM" ? "Gym · Equipe" : badge.label}</span>
        <span className="text-[10px] text-white/45">{is_virtual ? "Virtual" : "Oficial"}</span>
        {formattedDate && <span className="ml-auto text-[10px] text-white/50">{formattedDate}</span>}
      </div>
      <div className="mb-5 flex items-start justify-between gap-3">
        <h3 className="min-h-10 text-sm font-semibold leading-relaxed text-white/90">{contest_name}</h3>
        <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-white/25 transition-colors group-hover:text-red-300" />
      </div>
      <div className="mb-3 mt-auto flex items-end justify-between gap-3">
        <div><span className="text-2xl font-bold tabular-nums text-emerald-400">{progress.solved_live}</span><span className="ml-1 text-sm text-white/45">/ {progress.total}</span><p className="mt-0.5 text-[10px] text-white/50">ACs na prova</p></div>
        <div className="text-right"><p className="text-sm font-semibold tabular-nums text-sky-300">+{progress.upsolved}</p><p className="mt-0.5 text-[10px] text-white/50">{progress.upsolved === 1 ? 'upsolvada' : 'upsolvadas'}</p></div>
      </div>
      <ContestProgressBar {...progress} />
      <div className="mt-3 flex min-h-4 items-center justify-between gap-2 text-[10px] text-white/50">
        <span>{progress.pending_upsolve ? `${progress.pending_upsolve} para estudar` : "Ver questões e resultados"}</span>
        {participation.rank_context && rank != null && <span className="inline-flex items-center gap-1 text-amber-300"><Trophy className="size-3" />#{rank} · {participation.rank_context === "VIRTUAL" ? "virtual" : "oficial"}</span>}
      </div>
    </Link>
  );
}
