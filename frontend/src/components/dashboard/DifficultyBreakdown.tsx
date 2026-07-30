import { motion } from "framer-motion";

interface DifficultyBreakdownProps {
  data: Record<string, number>;
}

export function DifficultyBreakdown({ data }: DifficultyBreakdownProps) {
  // Configuração das faixas de dificuldade competitiva baseadas nos breakpoints do Codeforces
  const tiersConfig = [
    { label: "< 1200", min: 0, max: 1199, color: "bg-zinc-400" },
    { label: "1200 - 1399", min: 1200, max: 1399, color: "bg-emerald-400" },
    { label: "1400 - 1599", min: 1400, max: 1599, color: "bg-cyan-400" },
    { label: "1600 - 1899", min: 1600, max: 1899, color: "bg-blue-500" },
    { label: "1900 - 2099", min: 1900, max: 2099, color: "bg-purple-500" },
    { label: "2100 - 2399", min: 2100, max: 2399, color: "bg-orange-400" },
    { label: "2400 - 2999", min: 2400, max: 2999, color: "bg-red-500" },
    { label: "3000+", min: 3000, max: 99999, color: "bg-red-700" },
  ];

  // Somar total de problemas
  const total = Object.values(data).reduce((acc, count) => acc + count, 0);

  // Mapear contagem por faixa
  const tierCounts: Record<string, number> = {};
  tiersConfig.forEach((t) => { tierCounts[t.label] = 0; });

  Object.entries(data).forEach(([ratingStr, count]) => {
    const rating = parseInt(ratingStr);
    if (isNaN(rating) || rating === 0) return;

    const tier = tiersConfig.find((t) => rating >= t.min && rating <= t.max);
    if (tier) {
      tierCounts[tier.label] += count;
    } else if (rating < 1200) {
      tierCounts["< 1200"] += count;
    } else {
      tierCounts["3000+"] += count;
    }
  });

  // Filtrar apenas faixas que tenham pelo menos 1 problema resolvido
  const activeTiers = tiersConfig
    .map((tier) => ({
      ...tier,
      count: tierCounts[tier.label] || 0,
    }))
    .filter((t) => t.count > 0);

  const maxCount = Math.max(...activeTiers.map((t) => t.count), 1);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.7 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 h-full flex flex-col justify-between"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">POR DIFICULDADE</h3>
        <span className="text-xs text-zinc-500">{total} classificados</span>
      </div>

      <div className="flex flex-col gap-3 flex-1 justify-center">
        {activeTiers.map((tier, idx) => {
          const width = Math.max((tier.count / maxCount) * 100, 2);
          
          return (
            <div key={idx} className="flex items-center gap-3">
              <span className="w-24 text-xs font-medium text-zinc-400 text-right whitespace-nowrap">
                {tier.label}
              </span>
              <div className="flex-1 h-2 bg-zinc-800/50 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${width}%` }}
                  transition={{ duration: 1, delay: 0.8 + (idx * 0.05), ease: "easeOut" }}
                  className={`h-full rounded-full ${tier.color}`}
                />
              </div>
              <span className="w-10 text-xs font-bold text-zinc-300 text-left">
                {tier.count}
              </span>
            </div>
          );
        })}
        {activeTiers.length === 0 && (
          <div className="text-center py-4 text-sm text-zinc-600">Nenhum dado de dificuldade.</div>
        )}
      </div>
    </motion.div>
  );
}
