import { motion } from "framer-motion";
import type { Last7DaysStats } from "@/lib/api-dashboard";


interface Last7DaysWidgetProps {
  data: Last7DaysStats;
}

export function Last7DaysWidget({ data }: Last7DaysWidgetProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.6 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-4 flex flex-col h-full"
    >
      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest mb-3">ÚLTIMOS 7 DIAS</h3>

      <div className="flex justify-between items-center mb-3">
        {data.activity.map((isActive, idx) => (
          <div key={idx} className="flex flex-col items-center gap-2" title={data.dates?.[idx]}>
            <span className="text-[10px] text-zinc-400">{data.dates?.[idx] ? new Date(`${data.dates[idx]}T00:00:00Z`).toLocaleDateString('pt-BR', { weekday: 'short', timeZone: 'UTC' }).replace('.', '') : '—'}</span>
            <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 ${
              isActive
                ? 'bg-forja/10 border border-forja/30'
                : 'bg-zinc-800/50 text-zinc-400'
            }`}>
              <span role="img" aria-label={isActive ? "Dia com atividade" : "Dia sem atividade"} className={`size-2 rounded-full ${isActive ? "bg-red-400" : "bg-zinc-600"}`} />
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-y-2 gap-x-4 mt-auto border-t border-zinc-800/50 pt-2">
        <div>
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Total Resolvido</span>
          <span className="text-2xl font-black text-zinc-100">
            {data.total_solved}
          </span>
        </div>

        <div>
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-1">Dif. Média</span>
          <span className="text-2xl font-black text-zinc-100">
            {data.average_difficulty || '-'}
          </span>
        </div>

        <div className="col-span-2">
          <span className="block text-[10px] text-zinc-500 uppercase tracking-wider mb-2">Tópicos Frequentes</span>
          <div className="flex flex-wrap gap-2">
            {data.top_topics.length > 0 ? data.top_topics.map((t, idx) => (
              <div key={idx} className="px-2 py-0.5 bg-zinc-800/80 rounded border border-zinc-700/50 text-xs font-medium text-zinc-300 flex items-center gap-2">
                <span className="capitalize">{t.name}</span>
                <span className="text-red-400 font-bold">{t.count}</span>
              </div>
            )) : (
              <span className="text-xs text-zinc-400">Nenhum assunto explorado</span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
