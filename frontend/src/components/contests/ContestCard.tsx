import { useNavigate } from "react-router-dom";
import { ContestProgressBar } from "./ContestProgressBar";
import { Trophy, Swords, FlaskConical, ArrowRight } from "lucide-react";

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
}

const PLATFORM_BADGE: Record<string, { label: string; cls: string }> = {
  CF_OFFICIAL: { label: "CF Oficial",  cls: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
  CF_GYM:      { label: "CF Gym",      cls: "bg-purple-500/10 text-purple-400 border-purple-500/20" },
  ATCODER:     { label: "AtCoder",     cls: "bg-orange-500/10 text-orange-400 border-orange-500/20" },
};

export function ContestCard({ participation }: { participation: ContestParticipation }) {
  const navigate = useNavigate();
  const { 
    contest_id, contest_name, contest_platform, participation_date, 
    is_virtual, has_debt, progress, url, rank, solve_count, upsolve_count, total_problems 
  } = participation;

  const badge = PLATFORM_BADGE[contest_platform] ?? { label: contest_platform, cls: "bg-white/5 text-white/40 border-white/10" };

  const formattedDate = participation_date
    ? new Date(participation_date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" })
    : null;

  return (
    <div
      onClick={() => navigate(`/contests/${contest_id}`, { state: { contest_name, url, rank, progress } })}
      className="group relative w-full text-left rounded-2xl border border-white/[0.04] bg-[#0a0a0a]/80 backdrop-blur-xl p-6 cursor-pointer overflow-hidden transition-all duration-300 hover:border-[#dc143c]/30 hover:bg-[#110a0a]/80 hover:shadow-[0_0_30px_rgba(220,20,60,0.06)] hover:-translate-y-0.5 flex flex-col"
    >
      {/* Subtle top accent line */}
      <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-[#dc143c]/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      {/* Cabeçalho: badge + data */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-md border ${badge.cls} tracking-wide uppercase`}>
            {badge.label}
          </span>
          {is_virtual && (
            <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-md border bg-white/5 text-white/30 border-white/10 tracking-wide uppercase">
              Virtual
            </span>
          )}
          {rank !== null && rank !== undefined && (
            <span className="text-[10px] font-bold px-2 py-0.5 rounded-md border bg-yellow-500/10 text-yellow-500 border-yellow-500/20 flex items-center gap-1">
              <Trophy className="w-2.5 h-2.5" />
              #{rank}
            </span>
          )}
        </div>
        {formattedDate && (
          <span className="text-[11px] font-medium text-white/20 uppercase tracking-widest">{formattedDate}</span>
        )}
      </div>

      {/* Nome do contest */}
      <div className="flex items-start justify-between gap-4 mb-5">
        <h3 className="text-[15px] font-bold text-white/80 leading-snug line-clamp-2 group-hover:text-white transition-colors">
          {contest_name}
        </h3>
        <div className="w-6 h-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shrink-0 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-300 group-hover:bg-[#dc143c]/10 group-hover:border-[#dc143c]/20 group-hover:text-[#dc143c]">
          <ArrowRight className="w-3 h-3" />
        </div>
      </div>

      {/* Barra de progresso */}
      <ContestProgressBar {...progress} className="mb-4" />

      {/* Contagens textuais */}
      <div className="flex items-center gap-4 text-[11px] font-semibold tracking-wide">
        {progress.solved_live > 0 && (
          <span className="flex items-center gap-1.5 text-emerald-500/90">
            <Trophy className="w-3 h-3" />
            {progress.solved_live} AC LIVE
          </span>
        )}
        {progress.upsolved > 0 && (
          <span className="flex items-center gap-1.5 text-blue-400/90">
            <FlaskConical className="w-3 h-3" />
            {progress.upsolved} UPSOLVED
          </span>
        )}
        {has_debt && (
          <span className="flex items-center gap-1.5 ml-auto px-2 py-0.5 rounded-md bg-[#dc143c]/10 border border-[#dc143c]/20 text-[#dc143c]">
            <Swords className="w-3 h-3" />
            {progress.pending_upsolve} DÍVIDA{progress.pending_upsolve > 1 ? "S" : ""}
          </span>
        )}
      </div>
    </div>
  );
}
