import { useState } from "react";
import type { BenchmarkProblem, BenchmarkRun } from "./BenchmarkResults";

interface Props { problems: BenchmarkProblem[]; run: BenchmarkRun; onSelect: (keys: string[]) => void }
export function PredictionChart({ problems, run, onSelect }: Props) {
  const [active, setActive] = useState<string | null>(null);
  const groups = new Map<string, { actual: number; predicted: number; keys: string[] }>();
  for (const problem of problems) {
    const p = problem.predictions[run.id];
    if (p?.rating_status !== "valid" || p.rating == null || p.rating < 800 || p.rating > 2400) continue;
    const id = `${problem.reference.rating}:${p.rating}`;
    const group = groups.get(id) || { actual: problem.reference.rating, predicted: p.rating, keys: [] };
    group.keys.push(problem.key); groups.set(id, group);
  }
  const x = (r: number) => 72 + (r - 800) / 1600 * 610;
  const y = (r: number) => 350 - (r - 800) / 1600 * 300;
  const selected = active ? groups.get(active) : null;
  return <div className="relative">
    <svg viewBox="0 0 760 420" role="img" aria-label={`Rating previsto versus oficial — ${run.label}`} className="mx-auto w-full max-w-4xl text-zinc-500">
      <title>Rating previsto versus oficial</title><desc>Horizontal: rating oficial. Vertical: estimativa. A diagonal indica acerto. Pontos coincidentes são agrupados.</desc>
      {[800, 1200, 1600, 2000, 2400].map(tick => <g key={tick}>
        <line x1={x(tick)} y1="50" x2={x(tick)} y2="350" stroke="currentColor" opacity="0.13" />
        <line x1="72" y1={y(tick)} x2="682" y2={y(tick)} stroke="currentColor" opacity="0.13" />
        <text x={x(tick)} y="375" textAnchor="middle" fill="currentColor" fontSize="12">{tick}</text>
        <text x="59" y={y(tick) + 4} textAnchor="end" fill="currentColor" fontSize="12">{tick}</text>
      </g>)}
      <line x1="72" y1="350" x2="682" y2="50" stroke="#71717a" strokeDasharray="5 7" />
      <text x="470" y="32" fill="#a1a1aa" fontSize="12">↗ Estimativa correta</text>
      <text x="380" y="407" textAnchor="middle" fill="#d4d4d8" fontSize="13">Rating oficial</text>
      <text transform="translate(19 200) rotate(-90)" textAnchor="middle" fill="#d4d4d8" fontSize="13">Rating estimado</text>
      {[...groups].map(([id, point]) => <g key={id} role="button" tabIndex={0}
        aria-label={`Oficial ${point.actual}, estimado ${point.predicted} · ${point.keys.length} ${point.keys.length === 1 ? "problema" : "problemas"}`}
        className="group cursor-pointer outline-none" onFocus={() => setActive(id)} onMouseEnter={() => setActive(id)}
        onMouseLeave={() => setActive(null)} onBlur={() => setActive(null)}
        onClick={() => { setActive(id); onSelect(point.keys); }}
        onKeyDown={event => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); setActive(id); onSelect(point.keys); } }}>
        <circle cx={x(point.actual)} cy={y(point.predicted)} r="18" fill="transparent" />
        <circle cx={x(point.actual)} cy={y(point.predicted)} r={point.keys.length > 1 ? 8 : 5}
          fill={run.provider === "baseline" ? "#a1a1aa" : "#dc143c"} fillOpacity={active === id ? 1 : 0.55}
          stroke={active === id ? "#fafafa" : "#dc143c"} strokeOpacity={active === id ? 1 : 0.25} strokeWidth="2" />
        {point.keys.length > 1 && <text x={x(point.actual)} y={y(point.predicted) + 3} textAnchor="middle" fill="#fff" fontSize="9" pointerEvents="none">{point.keys.length}</text>}
      </g>)}
    </svg>
    <div className="min-h-12 border-t border-zinc-800 pt-3 text-xs text-zinc-400" aria-live="polite">
      {selected ? <p role="tooltip"><strong className="text-zinc-200">Oficial: {selected.actual}</strong> · Estimado: {selected.predicted} · {selected.predicted === selected.actual ? "Estimativa correta" : `${selected.predicted > selected.actual ? "Superestimou" : "Subestimou"} em ${Math.abs(selected.predicted - selected.actual)} pontos`} · {selected.keys.length} problema(s)</p>
        : "Acima da diagonal: superestimação. Abaixo: subestimação. Selecione um ponto para investigar; números nos pontos indicam agrupamentos."}
    </div>
  </div>;
}
