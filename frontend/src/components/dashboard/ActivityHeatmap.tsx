import { motion } from "framer-motion";
import type { HeatmapData } from "@/lib/api-dashboard";

interface ActivityHeatmapProps {
  data: HeatmapData[];
}

export function ActivityHeatmap({ data }: ActivityHeatmapProps) {
  // Converte array de api para dict mapeado por data
  const dataMap = new Map(data.map(d => [d.date, d.count]));

  // Gerar malha dos últimos 365 dias (52 semanas)
  const today = new Date();
  const days = [];
  
  // Voltando 364 dias
  for (let i = 364; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const dateStr = d.toISOString().split('T')[0];
    days.push({
      date: dateStr,
      count: dataMap.get(dateStr) || 0
    });
  }

  // Helper de cor baseado em Fogo/A Forja
  const getColor = (count: number) => {
    if (count === 0) return "bg-zinc-800/40";
    if (count < 3) return "bg-red-950";
    if (count < 6) return "bg-red-800";
    if (count < 10) return "bg-red-600";
    return "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]";
  };

  // Precisamos organizar num grid de colunas (semanas) e linhas (dias da semana)
  // O CSS Grid fará isso auto-flow se definirmos grid-rows-7 grid-flow-col
  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.5 }}
      className="bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 flex flex-col h-full"
    >
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">ATIVIDADE — ÚLTIMO ANO</h3>
        <span className="text-xs text-zinc-500">{data.length} dias ativos</span>
      </div>
      
      <div className="overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-zinc-700 scrollbar-track-transparent mt-auto">
        <div className="min-w-max">
          <div className="grid grid-rows-7 grid-flow-col gap-[2px]">
            {days.map((day, idx) => (
              <div
                key={day.date}
                className={`w-[14px] h-[14px] rounded-[2px] transition-all duration-300 hover:scale-125 ${getColor(day.count)}`}
                title={`${day.date}: ${day.count} submissões`}
              />
            ))}
          </div>
          
          <div className="flex items-center justify-end mt-4 text-[10px] text-zinc-500 font-medium tracking-wide gap-1">
            <span>Menos</span>
            <div className="w-[14px] h-[14px] rounded-[2px] bg-zinc-800/40"></div>
            <div className="w-[14px] h-[14px] rounded-[2px] bg-red-950"></div>
            <div className="w-[14px] h-[14px] rounded-[2px] bg-red-800"></div>
            <div className="w-[14px] h-[14px] rounded-[2px] bg-red-600"></div>
            <div className="w-[14px] h-[14px] rounded-[2px] bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]"></div>
            <span>Mais</span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
