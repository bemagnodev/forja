import { useState } from 'react';
import type { ContestParticipation } from './ContestCard';

export function ContestEvolution({ participations }: { participations: ContestParticipation[] }) {
  const [limit, setLimit] = useState(10);
  const [upsolving, setUpsolving] = useState(false);
  const [percentage, setPercentage] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const recent = [...participations].sort((a, b) => (Date.parse(b.participation_date ?? '') || 0) - (Date.parse(a.participation_date ?? '') || 0)).slice(0, limit).reverse();
  const selected = recent.find(p => p.id === selectedId);
  const scale = (p: ContestParticipation, n: number) => percentage ? (p.progress.total ? n / p.progress.total * 100 : 0) : n;
  const max = percentage ? 100 : Math.ceil(Math.max(1, ...recent.map(p => p.progress.solved_live + (upsolving ? p.progress.upsolved : 0))) / 2) * 2;
  return <section aria-label="Evolução nos contests" className="mt-8 rounded-2xl border border-white/[0.09] bg-[#101116] p-5 sm:p-6">
    <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
      <div><h3 className="text-sm font-semibold text-white/90">Evolução nos contests</h3><p className="mt-1 text-xs text-white/50">Resultado durante a prova · {recent.length} participações neste recorte</p></div>
      <div className="flex flex-wrap items-center gap-3 text-[11px] text-white/65">
        <label className="flex items-center gap-1.5"><input type="checkbox" checked={upsolving} onChange={e => setUpsolving(e.target.checked)} className="accent-sky-400" />Incluir upsolving</label>
        <label className="flex items-center gap-1.5"><input type="checkbox" checked={percentage} onChange={e => setPercentage(e.target.checked)} className="accent-sky-400" />Percentual</label>
        <select aria-label="Quantidade de contests no gráfico" value={limit} onChange={e => setLimit(Number(e.target.value))} className="rounded-lg border border-white/10 bg-[#15161d] p-2"><option value={10}>Últimos 10</option><option value={20}>Últimos 20</option></select>
      </div>
    </div>
    {!recent.length ? <p className="py-10 text-center text-sm text-white/45">Sem participações para exibir no gráfico.</p> : <>
      <div className="flex gap-3">
        <div aria-hidden="true" className="flex h-48 shrink-0 flex-col justify-between text-[10px] tabular-nums text-white/35"><span>{max}{percentage ? '%' : ''}</span><span>{Math.round(max / 2)}{percentage ? '%' : ''}</span><span>0</span></div>
        <div className="relative flex-1 overflow-x-auto pb-2">
          <div className="relative" style={{ minWidth: `${recent.length * 35}px` }}>
            <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 flex h-48 flex-col justify-between">{[0, 1, 2].map(i => <div key={i} className="border-t border-white/[0.06]" />)}</div>
            <div className="relative flex h-56 items-end gap-2">
              {recent.map((p, i) => <button key={p.id} onMouseEnter={() => setSelectedId(p.id)} onFocus={() => setSelectedId(p.id)} onClick={() => setSelectedId(p.id)}
                aria-label={`${p.contest_name}: ${p.progress.solved_live} ACs na prova de ${p.progress.total} questões${upsolving ? `, ${p.progress.upsolved} upsolvadas` : ''}`}
                className="group flex h-full min-w-6 flex-1 flex-col items-center justify-end rounded-t outline-none focus-visible:ring-2 focus-visible:ring-sky-400">
                <div className="flex h-48 w-full max-w-12 flex-col justify-end">
                  {upsolving && p.progress.upsolved > 0 && <div className="min-h-px rounded-t bg-sky-400/80" style={{ height: `${Math.min(100, scale(p, p.progress.upsolved) / max * 100)}%` }} />}
                  <div className="min-h-px rounded-t-sm bg-emerald-400/80 transition-colors group-hover:bg-emerald-300" style={{ height: `${Math.min(100, scale(p, p.progress.solved_live) / max * 100)}%` }} />
                </div>
                <span aria-hidden="true" className="mt-2 h-6 text-[10px] tabular-nums text-white/40">{String(i + 1).padStart(2, '0')}</span>
              </button>)}
            </div>
          </div>
        </div>
      </div>
      <div className="mt-3 flex flex-wrap justify-between gap-2 text-[10px] text-white/45"><span>Mais antigo → mais recente</span><div className="flex gap-4"><span><span className="mr-1.5 inline-block size-2 rounded-sm bg-emerald-400" />Na prova</span>{upsolving && <span><span className="mr-1.5 inline-block size-2 rounded-sm bg-sky-400" />Upsolving</span>}</div></div>
      <div role="status" className="mt-4 min-h-12 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-xs text-white/60">
        {selected ? <><span className="font-medium text-white/85">{selected.contest_name}</span><span className="mt-1 block">{selected.participation_date ? new Date(selected.participation_date).toLocaleDateString('pt-BR') : 'Data indisponível'} · {selected.progress.solved_live}/{selected.progress.total} na prova · +{selected.progress.upsolved} upsolvadas{selected.rank_context && selected.rank ? ` · #${selected.rank}` : ''}</span></> : 'Passe o cursor, toque ou navegue pelas barras para ver os resultados.'}
      </div>
    </>}
  </section>;
}
