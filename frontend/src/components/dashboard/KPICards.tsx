import { motion } from "framer-motion";
import type { DashboardKPIs } from "@/lib/api-dashboard";
import { CheckCircle2, Flame, Trophy, CalendarCheck } from "lucide-react";

interface KPICardsProps {
  kpis: DashboardKPIs;
}

export function KPICards({ kpis }: KPICardsProps) {
  const cards = [
    {
      title: "TOTAL RESOLVIDO",
      value: kpis.total_solved,
      subtitle: "INCLUI CONCLUSÕES MANUAIS",
      icon: <Trophy className="w-5 h-5 text-red-500/80" />,
      delay: 0.1,
    },
    {
      title: "SEQUÊNCIA ATUAL",
      value: `${kpis.streak}d`,
      subtitle: `MÁXIMO NO ANO: ${kpis.max_streak} DIAS`,
      icon: <Flame className="w-5 h-5 text-orange-500/80" />,
      delay: 0.2,
    },
    {
      title: "TAXA DE ACEITAÇÃO",
      value: `${kpis.acceptance_rate}%`,
      subtitle: "SUBMISSÕES ACEITAS / TOTAL",
      icon: <CheckCircle2 className="w-5 h-5 text-emerald-500/80" />,
      delay: 0.3,
    },
    {
      title: "ÚLTIMOS 30 DIAS",
      value: kpis.solved_this_month,
      subtitle: "PROBLEMAS COM AC",
      icon: <CalendarCheck className="w-5 h-5 text-red-400/80" />,
      delay: 0.4,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card, idx) => (
        <motion.div
          key={idx}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: card.delay }}
          className="relative group bg-zinc-900/50 backdrop-blur-md border border-zinc-800 rounded-xl p-5 overflow-hidden transition-all duration-300 hover:bg-zinc-900 hover:border-red-900/50"
        >
          {/* Sutil Glow de Hover */}
          <div className="absolute inset-0 bg-gradient-to-br from-red-500/0 via-red-500/0 to-red-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">{card.title}</h3>
            {card.icon}
          </div>
          
          <div className="flex flex-col">
            <span className="text-4xl font-black text-zinc-100 tracking-tight" style={{ fontFamily: 'Clash Display, system-ui, sans-serif' }}>
              {card.value}
            </span>
            <span className="text-xs text-zinc-500 mt-2 font-medium tracking-wide">
              {card.subtitle}
            </span>
          </div>
        </motion.div>
      ))}
    </div>
  );
}
