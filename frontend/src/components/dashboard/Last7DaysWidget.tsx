import { motion } from "framer-motion";
import type { Last7DaysStats } from "@/lib/api-dashboard";
import { Check, X } from "lucide-react";

interface Last7DaysWidgetProps {
  data: Last7DaysStats;
}

export function Last7DaysWidget({ data }: Last7DaysWidgetProps) {
  const days = ['S', 'M', 'T', 'W', 'T', 'F', 'S']; // Supondo último dia = Sábado/Domingo (meramente ilustrativo para o visual 7 dias)
  
  // Como last_7_days.activity tem os últimos 7 dias sequenciais,
  // Podemos mapear de 0 a 6
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 flex flex-col h-full"
    >
      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-6">LAST 7 DAYS</h3>
      
      <div className="flex justify-between items-center mb-8 px-2">
        {data.activity.map((isActive, idx) => (
          <div key={idx} className="flex flex-col items-center gap-2">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300 ${
              isActive 
                ? 'bg-red-500/20 text-red-500 shadow-[0_0_12px_rgba(239,68,68,0.3)]' 
                : 'bg-zinc-800/50 text-zinc-600'
            }`}>
              {isActive ? <Check className="w-4 h-4 stroke-[3]" /> : <X className="w-4 h-4" />}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-y-6 gap-x-4 mt-auto border-t border-zinc-800/50 pt-6">
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Total Solved</span>
          <span className="text-2xl font-black text-zinc-100" style={{ fontFamily: 'Clash Display, system-ui, sans-serif' }}>
            {data.total_solved}
          </span>
        </div>
        
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Avg Difficulty</span>
          <span className="text-2xl font-black text-zinc-100" style={{ fontFamily: 'Clash Display, system-ui, sans-serif' }}>
            {data.average_difficulty || '-'}
          </span>
        </div>
        
        <div className="col-span-2">
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Top Topics</span>
          <div className="flex flex-wrap gap-2">
            {data.top_topics.length > 0 ? data.top_topics.map((t, idx) => (
              <div key={idx} className="px-2 py-1 bg-zinc-800/80 rounded border border-zinc-700/50 text-xs font-medium text-zinc-300 flex items-center gap-2">
                <span className="capitalize">{t.name}</span>
                <span className="text-red-400 font-bold">{t.count}</span>
              </div>
            )) : (
              <span className="text-xs text-zinc-600">Nenhum assunto explorado</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
