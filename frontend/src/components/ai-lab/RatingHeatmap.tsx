import type { BenchmarkRun, RatingBand } from "./BenchmarkResults";

export function RatingHeatmap({ bands, runs }: { bands: RatingBand[]; runs: BenchmarkRun[] }) {
  const max = Math.max(1, ...bands.flatMap(b => Object.values(b.mae).filter((v): v is number => v != null)));
  return <div className="overflow-x-auto"><table className="w-full min-w-[540px] text-center text-sm">
    <caption className="sr-only">Erro médio por faixa de rating oficial</caption>
    <thead><tr><th className="p-3 text-left text-xs font-medium text-zinc-400">Modelo</th>{bands.map(b => <th key={b.label} className="p-3 text-xs font-medium text-zinc-400">{b.label}</th>)}</tr></thead>
    <tbody>{runs.map(run => <tr key={run.id}><th className="p-3 text-left text-xs font-medium text-zinc-300">{run.label}</th>
      {bands.map(band => { const value = band.mae[run.id]; return <td key={band.label} className="p-1.5"><div className="rounded-lg border border-zinc-800 p-3"
        style={{ backgroundColor: value == null ? "transparent" : `rgba(220,20,60,${0.035 + 0.45 * value / max})` }}>
        <span className="font-mono font-semibold text-zinc-100">{value == null ? "—" : Math.round(value)}</span>
        <span className="mt-1 block text-[10px] text-zinc-400">{band.compared}/{band.total} comparados</span>
      </div></td>; })}</tr>)}</tbody>
  </table><div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-zinc-400"><span className="flex items-center gap-2">Menor erro <span className="h-2 w-20 rounded bg-gradient-to-r from-zinc-900 to-forja/60" /> Maior erro</span><span>0–{Math.ceil(max)} pontos · menor erro é melhor</span></div></div>;
}
