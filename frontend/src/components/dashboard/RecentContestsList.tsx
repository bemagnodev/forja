import { motion } from "framer-motion";
import type { RecentContest } from "@/lib/api-dashboard";
import { useNavigate } from "react-router-dom";

interface RecentContestsListProps {
  data: RecentContest[];
}

export function RecentContestsList({ data }: RecentContestsListProps) {
  const navigate = useNavigate();

  const getPlatformBadge = (platform: string) => {
    switch (platform) {
      case 'CF_OFFICIAL':
      case 'CF_GYM':
        return <img src="/logos/code-forces.png" alt="CF" className="size-5 shrink-0 object-contain rounded-none" />;
      case 'ATCODER':
        return <img src="/logos/atCoder.png" alt="AT" className="size-5 shrink-0 object-contain rounded-none" />;
      case 'CSES':
        return <img src="/logos/cses.png" alt="CS" className="size-5 shrink-0 object-contain rounded-none" />;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-zinc-300">{platform}</span>;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.9 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 transition-colors rounded-xl p-5 flex flex-col"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest cursor-pointer hover:text-white transition-colors" onClick={() => navigate('/contests')}>
          CONTESTS RECENTES &rarr;
        </h3>
      </div>

      <div className="flex flex-col gap-3">
        {data.map((contest, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 1 + (idx * 0.1) }}
            onClick={() => navigate(`/contests/${contest.contest_id}`)}
            className="flex flex-col gap-2 p-3 rounded-lg border border-zinc-800/50 bg-zinc-900/30 hover:bg-zinc-800/60 transition-colors cursor-pointer group"
          >
            <div className="flex justify-between items-start">
              <div className="flex min-w-0 items-center gap-2">
                {getPlatformBadge(contest.platform)}
                <span className="text-sm font-semibold text-zinc-200 transition-colors line-clamp-1">{contest.name}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-xs mt-1">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                <span className="text-emerald-400 font-medium">{contest.progress.solved_live} na prova</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                <span className="text-cyan-400 font-medium">{contest.progress.upsolved} upsolvadas</span>
              </div>
              {contest.progress.pending_upsolve > 0 && (
                <div className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                  <span className="text-orange-400 font-medium">{contest.progress.pending_upsolve} Pendentes</span>
                </div>
              )}
            </div>
          </motion.div>
        ))}
        
        {data.length === 0 && (
          <div className="text-center py-8 text-sm text-zinc-400">Nenhum contest participado recentemente.</div>
        )}
      </div>
    </motion.div>
  );
}
