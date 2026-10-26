import { Trophy, Swords, FlaskConical, LayoutGrid } from "lucide-react";
import type { ContestParticipation } from "./ContestCard";

// Header com 4 métricas globais calculadas a partir da lista de contests
export function ContestMetrics({ participations }: { participations: ContestParticipation[] }) {
  const totalContests = participations.length;
  const totalLive     = participations.reduce((acc, p) => acc + p.progress.solved_live, 0);
  const totalDebts    = participations.reduce((acc, p) => acc + p.progress.pending_upsolve, 0);
  const totalUpsolved = participations.reduce((acc, p) => acc + p.progress.upsolved, 0);

  const metrics = [
    { label: "Contests",        value: totalContests, icon: LayoutGrid,    color: "text-white/60",    bg: "bg-white/[0.04]",          border: "border-white/[0.07]" },
    { label: "AC Live",         value: totalLive,     icon: Trophy,         color: "text-emerald-400", bg: "bg-emerald-500/[0.06]",    border: "border-emerald-500/[0.12]" },
    { label: "Dívidas Abertas", value: totalDebts,    icon: Swords,         color: "text-[#dc143c]",   bg: "bg-[#dc143c]/[0.06]",      border: "border-[#dc143c]/[0.12]" },
    { label: "Upsolvados",      value: totalUpsolved, icon: FlaskConical,   color: "text-blue-400",    bg: "bg-blue-500/[0.06]",       border: "border-blue-500/[0.12]" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
      {metrics.map(({ label, value, icon: Icon, color, bg, border }) => (
        <div key={label} data-testid={label === 'Contests' ? 'metric-contests' : undefined} className={`rounded-xl border ${border} ${bg} px-4 py-3 flex items-center gap-3`}>
          <div className={`w-8 h-8 rounded-lg ${bg} border ${border} flex items-center justify-center shrink-0`}>
            <Icon className={`w-4 h-4 ${color}`} strokeWidth={1.75} />
          </div>
          <div>
            <p className={`text-[22px] font-extrabold leading-none ${color}`}>{value}</p>
            <p className="text-[10px] text-white/55 tracking-wide font-medium mt-1">{label === 'AC Live' ? 'ACs na prova' : label === 'Dívidas Abertas' ? 'Para estudar' : label === 'Upsolvados' ? 'Upsolvadas' : label}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
