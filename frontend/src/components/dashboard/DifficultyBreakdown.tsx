import { motion } from "framer-motion";

interface DifficultyBreakdownProps {
  data: Record<string, number>;
}

export function DifficultyBreakdown({ data }: DifficultyBreakdownProps) {
  // Ordenar buckets de dificuldade
  const buckets = Object.entries(data)
    .map(([rating, count]) => ({ rating: parseInt(rating), count }))
    .sort((a, b) => a.rating - b.rating);

  const maxCount = Math.max(...buckets.map(b => b.count), 1);
  const total = buckets.reduce((acc, b) => acc + b.count, 0);

  // Sistema de cor de rating baseado no Codeforces/Comum
  const getRatingColor = (rating: number) => {
    if (rating < 1200) return "bg-zinc-400"; // Gray
    if (rating < 1400) return "bg-emerald-400"; // Green
    if (rating < 1600) return "bg-cyan-400"; // Cyan
    if (rating < 1900) return "bg-blue-500"; // Blue
    if (rating < 2100) return "bg-purple-500"; // Purple
    if (rating < 2400) return "bg-orange-400"; // Orange
    return "bg-red-500"; // Red
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.7 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">DIFFICULTY BREAKDOWN</h3>
        <span className="text-xs text-zinc-500">{total} rated problems</span>
      </div>

      <div className="flex flex-col gap-3">
        {buckets.map((bucket, idx) => {
          const width = Math.max((bucket.count / maxCount) * 100, 2); // Min 2% para ficar visível
          
          return (
            <div key={idx} className="flex items-center gap-3">
              <span className="w-10 text-xs font-medium text-zinc-400 text-right">
                {bucket.rating === 0 ? '?' : bucket.rating}
              </span>
              <div className="flex-1 h-2 bg-zinc-800/50 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${width}%` }}
                  transition={{ duration: 1, delay: 0.8 + (idx * 0.05), ease: "easeOut" }}
                  className={`h-full rounded-full ${getRatingColor(bucket.rating)}`}
                />
              </div>
              <span className="w-8 text-xs font-bold text-zinc-300 text-left">
                {bucket.count}
              </span>
            </div>
          );
        })}
        {buckets.length === 0 && (
          <div className="text-center py-4 text-sm text-zinc-600">Nenhum dado de dificuldade.</div>
        )}
      </div>
    </motion.div>
  );
}
