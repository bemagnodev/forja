import { motion } from "framer-motion";
import type { TopicStat } from "@/lib/api-dashboard";

interface TopicMasteryProps {
  data: TopicStat[];
}

export function TopicMastery({ data }: TopicMasteryProps) {
  const maxSolved = Math.max(...data.map(t => t.solved), 1);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.8 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 col-span-1 lg:col-span-2 h-full flex flex-col"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">RESOLVIDOS POR TÓPICO</h3>
        <span className="text-xs text-zinc-500">{data.length} mais frequentes</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-x-8 gap-y-4">
        {data.map((topic, idx) => {
          const width = Math.max((topic.solved / maxSolved) * 100, 2);
          
          return (
            <div key={idx} className="flex flex-col gap-1">
              <div className="flex justify-between items-end">
                <span className="text-xs font-medium text-zinc-300 capitalize truncate pr-2">{topic.name}</span>
                <span className="text-xs font-bold text-red-500">{topic.solved}</span>
              </div>
              <div className="h-1.5 w-full bg-zinc-800/50 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${width}%` }}
                  transition={{ duration: 1, delay: 0.9 + (idx * 0.05), ease: "easeOut" }}
                  className="h-full bg-gradient-to-r from-red-800 to-red-500 rounded-full"
                />
              </div>
            </div>
          );
        })}
        {data.length === 0 && (
          <div className="col-span-3 text-center py-8 text-sm text-zinc-600">Nenhum dado de tópicos.</div>
        )}
      </div>
    </motion.div>
  );
}
