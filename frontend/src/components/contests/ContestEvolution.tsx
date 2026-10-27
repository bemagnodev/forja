import { useState } from 'react';
import { TrendingUp } from 'lucide-react';
import type { ContestParticipation } from './ContestCard';

type Mode = 'solves' | 'rank' | 'penalty';
const modes: { key: Mode; label: string }[] = [{ key: 'solves', label: 'Resoluções' }, { key: 'rank', label: 'Ranking' }, { key: 'penalty', label: 'Penalidade' }];
const ranked = (p: ContestParticipation) => !!p.rank_context && p.rank != null && p.rank > 0;
const date = (p: ContestParticipation) => p.participation_date ? new Date(p.participation_date).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' }) : 'Data indisponível';

export function ContestEvolution({ participations }: { participations: ContestParticipation[] }) {
  const [mode, setMode] = useState<Mode>('solves');
  const [limit, setLimit] = useState(10);
  const [upsolving, setUpsolving] = useState(false);
  const [percentage, setPercentage] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const recent = [...participations].sort((a, b) => (Date.parse(b.participation_date ?? '') || 0) - (Date.parse(a.participation_date ?? '') || 0)).slice(0, limit).reverse();
  const selected = recent.find(p => p.id === selectedId);
  const value = (p: ContestParticipation) => mode === 'rank' ? (ranked(p) ? p.rank! : null)
    : mode === 'penalty' ? (ranked(p) && p.penalty != null ? p.penalty : null) : p.progress.solved_live;
  const values = recent.map(value).filter((n): n is number => n != null);
  const scaleSolve = (p: ContestParticipation, n: number) => percentage ? (p.progress.total ? n / p.progress.total * 100 : 0) : n;
  const largest = Math.max(1, ...recent.map(p => mode === 'solves' ? Math.max(scaleSolve(p, p.progress.solved_live), upsolving ? scaleSolve(p, p.progress.upsolved) : 0) : value(p) ?? 0));
  const step = largest > 100 ? 100 : largest > 10 ? 10 : 2;
  const max = mode === 'solves' && percentage ? 100 : Math.ceil(largest / step) * step;
  const rankMin = Math.min(...values, 1e9), rankMax = Math.max(...values, 1);
  const low = rankMin === rankMax ? Math.max(1, rankMin - 1) : rankMin;
  const high = rankMin === rankMax ? rankMax + 1 : rankMax;
  const yRank = (rank: number) => 12 + (rank - low) / Math.max(1, high - low) * 168;
  const rankSegments: string[][] = [[]];
  if (mode === 'rank') recent.forEach((p, i) => {
    const rank = value(p);
    if (rank == null) { if (rankSegments.at(-1)!.length) rankSegments.push([]); }
    else rankSegments.at(-1)!.push(`${(i + .5) / recent.length * 1000},${yRank(rank)}`);
  });
  const total = recent.reduce((n, p) => n + p.progress.total, 0);
  const live = recent.reduce((n, p) => n + p.progress.solved_live, 0);
  const stats = mode === 'solves' ? [
    { label: 'Aproveitamento na prova', value: total ? `${Math.round(live / total * 100)}%` : '—' },
    { label: 'Média de ACs', value: recent.length ? (live / recent.length).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) : '—' },
    { label: 'Upsolvadas no recorte', value: String(recent.reduce((n, p) => n + p.progress.upsolved, 0)) },
  ] : [
    { label: mode === 'rank' ? 'Melhor posição' : 'Menor penalidade', value: values.length ? `${mode === 'rank' ? '#' : ''}${Math.min(...values)}${mode === 'penalty' ? ' min' : ''}` : '—' },
    { label: mode === 'rank' ? 'Participações com ranking' : 'Participações com penalidade', value: `${values.length} / ${recent.length}` },
    { label: mode === 'rank' ? 'Fonte' : 'Média da penalidade', value: mode === 'rank' ? 'Placar CF' : values.length ? `${Math.round(values.reduce((a, b) => a + b, 0) / values.length)} min` : '—' },
  ];
  const axis = mode === 'rank' ? (values.length ? [`#${low}`, `#${Math.round((low + high) / 2)}`, `#${high}`] : ['—', '—', '—'])
    : [String(max) + (percentage && mode === 'solves' ? '%' : ''), String(max / 2) + (percentage && mode === 'solves' ? '%' : ''), '0'];
  const barLabel = (p: ContestParticipation) => mode === 'solves' ? `${p.contest_name}: ${p.progress.solved_live} ACs na prova de ${p.progress.total} questões${upsolving ? `, ${p.progress.upsolved} ${p.progress.upsolved === 1 ? 'upsolvada' : 'upsolvadas'}` : ''}`
    : mode === 'rank' ? `${p.contest_name}: ${value(p) == null ? 'ranking indisponível' : `posição ${value(p)}, ${p.rank_context === 'VIRTUAL' ? 'virtual' : 'oficial'}`}`
    : `${p.contest_name}: ${value(p) == null ? 'penalidade indisponível' : `penalidade ${value(p)} min`}`;

  return <section aria-label="Evolução nos contests" className="mt-8 overflow-hidden rounded-xl border border-zinc-800 bg-zinc-900/40">
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 px-5 py-5 sm:px-6">
      <div className="flex items-center gap-3"><TrendingUp className="size-5 text-forja" /><div><h3 className="text-sm font-semibold text-zinc-100">Evolução nos contests</h3><p className="mt-1 text-[11px] text-zinc-500">{recent.length} participações · mais antigo → mais recente</p></div></div>
      <div role="tablist" aria-label="Métrica da evolução" className="flex rounded-lg border border-zinc-800 bg-zinc-950/60 p-1">
        {modes.map((m, i) => <button role="tab" key={m.key} data-mode={m.key} aria-selected={mode === m.key} tabIndex={mode === m.key ? 0 : -1} onClick={() => setMode(m.key)}
          onKeyDown={e => { if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key)) { e.preventDefault(); const next = e.key === 'Home' ? 0 : e.key === 'End' ? 2 : (i + (e.key === 'ArrowRight' ? 1 : 2)) % 3; setMode(modes[next].key); e.currentTarget.parentElement?.querySelector<HTMLElement>(`[data-mode="${modes[next].key}"]`)?.focus(); } }}
          className={`rounded-md px-3 py-2 text-[11px] font-semibold transition-colors focus-visible:outline focus-visible:outline-forja ${mode === m.key ? 'bg-forja/15 text-red-300' : 'text-zinc-500 hover:text-zinc-200'}`}>{m.label}</button>)}
      </div>
    </div>
    <div className="grid grid-cols-3 border-b border-zinc-800/70">{stats.map(s => <div key={s.label} className="border-r border-zinc-800/70 px-4 py-4 last:border-0 sm:px-6"><p className="text-xl font-bold tracking-tight tabular-nums text-zinc-100 sm:text-2xl">{s.value}</p><p className="mt-1 text-[10px] text-zinc-500">{s.label}</p></div>)}</div>
    <div className="p-5 sm:p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 text-[11px] text-zinc-500">
        <p>{mode === 'solves' ? 'ACs na prova e resoluções posteriores em barras separadas' : mode === 'rank' ? 'Menor posição é melhor' : 'Penalidade ICPC importada do placar'}</p>
        <div className="flex flex-wrap items-center gap-3">
          {mode === 'solves' && <><label className="flex items-center gap-1.5"><input type="checkbox" checked={upsolving} onChange={e => setUpsolving(e.target.checked)} className="accent-forja" />Incluir upsolving</label><label className="flex items-center gap-1.5"><input type="checkbox" checked={percentage} onChange={e => setPercentage(e.target.checked)} className="accent-forja" />Percentual</label></>}
          <select aria-label="Quantidade de contests no gráfico" value={limit} onChange={e => setLimit(Number(e.target.value))} className="rounded-lg border border-zinc-800 bg-zinc-950 p-2 text-zinc-300 outline-none focus-visible:ring-1 focus-visible:ring-forja"><option value={10}>Últimos 10</option><option value={20}>Últimos 20</option></select>
        </div>
      </div>
      {!recent.length ? <p className="py-12 text-center text-sm text-zinc-500">Sem participações para exibir no gráfico.</p> : <>
        <div className="flex gap-3">
          <div aria-hidden="true" className="flex h-48 w-8 shrink-0 flex-col justify-between text-[10px] tabular-nums text-zinc-600">{axis.map((a, i) => <span key={i}>{a}</span>)}</div>
          <div className="min-w-0 flex-1 overflow-x-auto pb-2"><div className="relative" style={{ minWidth: `${recent.length * (upsolving && mode === 'solves' ? 46 : 36)}px` }}>
            <div aria-hidden="true" className="pointer-events-none absolute inset-x-0 top-0 flex h-48 flex-col justify-between">{[0, 1, 2].map(i => <div key={i} className="border-t border-white/[0.05]" />)}</div>
            {mode === 'rank' && <svg aria-hidden="true" viewBox="0 0 1000 192" preserveAspectRatio="none" className="pointer-events-none absolute inset-x-0 top-0 h-48 w-full overflow-visible">{rankSegments.filter(s => s.length > 1).map((s, i) => <polyline key={i} points={s.join(' ')} fill="none" stroke="#dc143c" strokeWidth="2" vectorEffect="non-scaling-stroke" />)}</svg>}
            <div className="relative flex h-56 gap-2">
              {recent.map((p, i) => <button key={p.id} onMouseEnter={() => setSelectedId(p.id)} onFocus={() => setSelectedId(p.id)} onClick={() => setSelectedId(p.id)} aria-label={barLabel(p)} className="group flex h-full min-w-6 flex-1 flex-col items-center rounded-t outline-none focus-visible:ring-1 focus-visible:ring-forja">
                <div className="relative flex h-48 w-full items-end justify-center gap-1">
                  {mode === 'solves' ? <>
                    <div className="w-full max-w-7 rounded-t-sm bg-emerald-500/80 transition-colors group-hover:bg-emerald-400" style={{ height: `${Math.min(100, scaleSolve(p, p.progress.solved_live) / max * 100)}%` }} />
                    {upsolving && <div className="w-full max-w-7 rounded-t-sm bg-sky-500/70 transition-colors group-hover:bg-sky-400" style={{ height: `${Math.min(100, scaleSolve(p, p.progress.upsolved) / max * 100)}%` }} />}
                  </> : value(p) == null ? <span className="pb-2 text-zinc-700">—</span> : mode === 'rank'
                    ? <span className={`absolute size-2.5 rounded-full border-2 border-forja ${selectedId === p.id ? 'bg-forja' : 'bg-zinc-950'}`} style={{ top: `${yRank(value(p)!)}px`, transform: 'translateY(-50%)' }} />
                    : <div className="w-full max-w-9 rounded-t-sm bg-forja/65 transition-colors group-hover:bg-forja" style={{ height: `${value(p)! / max * 100}%` }} />}
                </div><span aria-hidden="true" className="mt-2 text-[10px] tabular-nums text-zinc-600">{String(i + 1).padStart(2, '0')}</span>
              </button>)}
            </div>
          </div></div>
        </div>
        <div className="mt-3 flex flex-wrap justify-between gap-2 text-[10px] text-zinc-500"><span>{mode === 'rank' ? 'Posições oficiais e virtuais preservam o contexto de cada prova.' : mode === 'penalty' ? 'Durações e formatos diferentes podem ter penalidades diferentes.' : 'Resultados por participação, na ordem dos treinos.'}</span>{mode === 'solves' && <span className="flex gap-3"><span><i className="mr-1.5 inline-block size-2 rounded-sm bg-emerald-500" />Na prova</span>{upsolving && <span><i className="mr-1.5 inline-block size-2 rounded-sm bg-sky-500" />Upsolving</span>}</span>}</div>
        <div role="status" className="mt-5 min-h-14 rounded-lg border border-zinc-800 border-l-forja/60 bg-zinc-950/60 px-4 py-3 text-xs text-zinc-500">
          {selected ? <><span className="font-semibold text-zinc-200">{selected.contest_name}</span><span className="mt-1 block">{date(selected)} · {selected.progress.solved_live}/{selected.progress.total} na prova · +{selected.progress.upsolved} {selected.progress.upsolved === 1 ? 'upsolvada' : 'upsolvadas'}{ranked(selected) ? ` · #${selected.rank} (${selected.rank_context === 'VIRTUAL' ? 'virtual' : 'oficial'})` : ''}{mode === 'penalty' && value(selected) != null ? ` · ${value(selected)} min` : ''}</span></> : 'Passe o cursor, toque ou navegue pelas barras para ver os resultados.'}
        </div>
        {mode !== 'solves' && values.length < recent.length && <p className="mt-3 text-[11px] text-zinc-500">{recent.length - values.length} participações sem {mode === 'rank' ? 'ranking' : 'penalidade'} confirmado. Dados ausentes ficam em branco.</p>}
      </>}
    </div>
  </section>;
}
