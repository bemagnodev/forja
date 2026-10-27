import { Link } from "react-router-dom";
import { ContestProgressBar } from "./ContestProgressBar";
import { Trophy, ArrowUpRight } from "lucide-react";
import { ContestIdentity } from './ContestIdentity';

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

export function ContestCard({ participation, onNavigate }: { participation: ContestParticipation; onNavigate?: () => void }) {
  const { 
    contest_id, contest_name, contest_platform, participation_date, 
    is_virtual, progress, url, rank
  } = participation;

  const formattedDate = participation_date
    ? new Date(participation_date).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" })
    : null;

  return (
    <Link to={`/contests/${contest_id}`} state={{ contest_name, url, rank, progress }} onClick={onNavigate}
      className="group relative flex min-h-[218px] flex-col overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/50 p-5 text-left transition-all duration-200 hover:border-forja/45 hover:bg-zinc-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-forja">
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-transparent to-forja/[0.04] opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="relative mb-4 flex flex-wrap items-center justify-between gap-2">
        <ContestIdentity platform={contest_platform} virtual={is_virtual} />
        {formattedDate && <time dateTime={participation_date!} className="text-[10px] tabular-nums text-zinc-500">{formattedDate}</time>}
      </div>
      <div className="mb-5 flex items-start justify-between gap-3">
        <h3 className="min-h-10 text-sm font-semibold leading-relaxed text-zinc-100 transition-colors group-hover:text-white">{contest_name}</h3>
        <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-white/25 transition-colors group-hover:text-red-300" />
      </div>
      <div className="mb-3 mt-auto flex items-end justify-between gap-3">
        <div><span className="text-4xl font-black tracking-tight tabular-nums text-emerald-400">{progress.solved_live}</span><span className="ml-1.5 text-lg font-semibold tabular-nums text-zinc-500">/ {progress.total}</span><p className="mt-1 text-[10px] text-zinc-500">ACs na prova</p></div>
        <div className="text-right"><p className="text-xl font-bold tabular-nums text-sky-300">+{progress.upsolved}</p><p className="mt-1 text-[10px] text-zinc-500">{progress.upsolved === 1 ? 'upsolvada' : 'upsolvadas'}</p></div>
      </div>
      <ContestProgressBar {...progress} />
      <div className="mt-3 flex min-h-4 items-center justify-between gap-2 text-[10px] text-white/50">
        <span className="text-red-300/80">{progress.pending_upsolve ? `${progress.pending_upsolve} ${progress.pending_upsolve === 1 ? 'pendência' : 'pendências'}` : null}</span>
        {participation.rank_context && rank != null && <span className="inline-flex items-center gap-1 text-amber-300"><Trophy className="size-3" />#{rank} · {participation.rank_context === "VIRTUAL" ? "virtual" : "oficial"}</span>}
      </div>
    </Link>
  );
}
