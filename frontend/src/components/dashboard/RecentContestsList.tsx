import { motion } from "framer-motion";
import { RecentContest } from "@/lib/api-dashboard";
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
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#1e457e] text-blue-200">CF</span>;
      case 'ATCODER':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#111] text-white border border-zinc-700">AT</span>;
      case 'CSES':
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-zinc-300">CS</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-zinc-300">{platform}</span>;
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.9 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 flex flex-col"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest cursor-pointer hover:text-white transition-colors" onClick={() => navigate('/contests')}>
          RECENT CONTESTS &rarr;
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
            className="flex flex-col gap-2 p-3 rounded-lg border border-zinc-800/50 bg-zinc-900/30 hover:bg-zinc-800 hover:border-zinc-700 transition-colors cursor-pointer group"
          >
            <div className="flex justify-between items-start">
              <div className="flex items-center gap-2">
                {getPlatformBadge(contest.platform)}
                <span className="text-sm font-semibold text-zinc-200 group-hover:text-red-400 transition-colors line-clamp-1">{contest.name}</span>
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-xs mt-1">
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                <span className="text-emerald-400 font-medium">{contest.progress.solved_live} Live</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-cyan-500"></div>
                <span className="text-cyan-400 font-medium">{contest.progress.upsolved} Upsolved</span>
              </div>
              {contest.progress.pending_upsolve > 0 && (
                <div className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
                  <span className="text-orange-400 font-medium">{contest.progress.pending_upsolve} Pending</span>
                </div>
              )}
            </div>
          </motion.div>
        ))}
        
        {data.length === 0 && (
          <div className="text-center py-8 text-sm text-zinc-600">Nenhum contest participado recentemente.</div>
        )}
      </div>
    </motion.div>
  );
}
