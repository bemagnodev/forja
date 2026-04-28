// Barra visual segmentada que representa o progresso de questões de um contest
interface ContestProgressBarProps {
  solved_live: number;
  pending_upsolve: number;
  upsolved: number;
  unattempted: number;
  total: number;
  className?: string;
}

export function ContestProgressBar({
  solved_live,
  pending_upsolve,
  upsolved,
  unattempted,
  total,
  className = "",
}: ContestProgressBarProps) {
  if (total === 0) return null;

  // Calcula largura percentual de cada segmento
  const pct = (n: number) => `${((n / total) * 100).toFixed(1)}%`;

  const segments = [
    { value: solved_live,    color: "bg-emerald-500",      title: "AC no Contest" },
    { value: upsolved,       color: "bg-blue-500",         title: "Upsolvado" },
    { value: pending_upsolve,color: "bg-amber-400",        title: "Pendente Upsolve" },
    { value: unattempted,    color: "bg-white/10",         title: "Não tentada" },
  ];

  return (
    <div className={`flex h-1.5 w-full gap-px rounded-full overflow-hidden ${className}`}>
      {segments.map((seg, i) =>
        seg.value > 0 ? (
          <div
            key={i}
            className={`${seg.color} transition-all`}
            style={{ width: pct(seg.value) }}
            title={`${seg.title}: ${seg.value}`}
          />
        ) : null
      )}
    </div>
  );
}
