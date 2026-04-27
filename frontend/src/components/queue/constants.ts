import { Flame, AlertCircle, ChevronUp, RotateCcw } from "lucide-react";

// Usamos explicitamente a cor primária #dc143c da nossa identidade visual para o P0
export const priorityConfig: Record<
  string,
  { border: string; text: string; bg: string; label: string; Icon: React.ElementType }
> = {
  P0:        { border: "#dc143c", text: "#e8234a", bg: "rgba(220,20,60,0.12)",  label: "P0 — Crítico",  Icon: Flame      },
  P1:        { border: "#d35400", text: "#e67e22", bg: "rgba(211,84,0,0.12)",   label: "P1 — Alto",     Icon: AlertCircle },
  P2:        { border: "#b7950b", text: "#f0c30f", bg: "rgba(183,149,11,0.12)", label: "P2 — Normal",   Icon: ChevronUp  },
  UPSOLVING: { border: "#5b4fcf", text: "#9b89e8", bg: "rgba(91,79,207,0.12)", label: "Upsolving",     Icon: RotateCcw  },
};

export const priorityOptions = Object.entries(priorityConfig).map(([value, cfg]) => ({
  value,
  label: cfg.label,
  color: cfg.border,
}));
