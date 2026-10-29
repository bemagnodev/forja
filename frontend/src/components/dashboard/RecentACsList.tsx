import { motion } from "framer-motion";
import type { RecentAC } from "@/lib/api-dashboard";

interface RecentACsListProps {
  data: RecentAC[];
}

export function RecentACsList({ data }: RecentACsListProps) {
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
        return <span className="px-1.5 py-0.5 rounded text-[11px] font-bold bg-zinc-800 text-zinc-300">{platform}</span>;
    }
  };

  const formatDate = (isoStr: string) => {
    const d = new Date(isoStr);
    return d.toLocaleDateString('pt-BR', { month: 'short', day: 'numeric' });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 1.0 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 transition-colors rounded-xl p-5 flex flex-col"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">QUESTÕES RECENTES</h3>
      </div>

      <div className="flex flex-col gap-2">
        {data.map((ac, idx) => (
          <motion.a 
            key={idx}
            href={ac.url || '#'}
            target={ac.url ? "_blank" : "_self"}
            rel="noopener noreferrer"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 1.1 + (idx * 0.05) }}
            className="flex items-center justify-between py-2 border-b border-zinc-800/30 last:border-0 hover:bg-zinc-800/60  rounded-md transition-all group cursor-pointer"
          >
            <div className="flex min-w-0 items-center gap-3">
              {getPlatformBadge(ac.platform)}
              <div className="min-w-0 flex-1 flex flex-col">
                <span className="text-sm font-medium text-zinc-300 line-clamp-1 transition-colors">{ac.problem_name}</span>
                <div className="flex gap-1 mt-0.5">
                  {ac.tags.slice(0, 2).map((t, i) => (
                    <span key={i} className="text-[11px] text-zinc-500 uppercase">{t}{i < Math.min(ac.tags.length, 2) - 1 ? ',' : ''}</span>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs font-bold text-emerald-500">AC</span>
              <span className="text-xs text-zinc-400">{formatDate(ac.date)}</span>
            </div>
          </motion.a>
        ))}
        
        {data.length === 0 && (
          <div className="text-center py-8 text-sm text-zinc-400">Nenhum AC recente.</div>
        )}
      </div>
    </motion.div>
  );
}
