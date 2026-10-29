import { Scale } from 'lucide-react';
import { getRatingColor } from '@/lib/ratings';

interface Props {
  realRating: number | null;
  predictedRating: number | null;
  ratingStatus: string;
  realTags: string[];
}

export function ReferenceComparison({ realRating, predictedRating, ratingStatus, realTags }: Props) {
  const hasReference = realRating != null && Number.isFinite(realRating) && realRating > 0;
  const hasEstimate = ratingStatus === 'valid' && predictedRating != null && Number.isFinite(predictedRating);
  const delta = hasReference && hasEstimate ? predictedRating! - realRating! : null;
  const direction = delta == null ? '' : delta === 0 ? 'Rating exato' : `${delta > 0 ? 'Superestimou' : 'Subestimou'} em ${Math.abs(delta)} pontos`;
  return <section aria-label="Comparação com referência" className="rounded-xl border border-zinc-800 bg-zinc-900/30 p-4 sm:p-5">
    <h3 className="flex items-center gap-2 text-sm font-semibold text-zinc-100"><Scale className="size-4 text-zinc-400" />Estimativa × referência oficial</h3>
    <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3"><p className="mb-1 text-xs text-zinc-400">Oficial</p><p aria-label="Rating oficial" className="font-mono text-2xl font-bold tabular-nums" style={{ color: hasReference ? getRatingColor(realRating) : undefined }}>{hasReference ? realRating : '—'}</p></div>
      <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3"><p className="mb-1 text-xs text-zinc-400">Estimado</p><p aria-label="Rating estimado" className="font-mono text-2xl font-bold tabular-nums" style={{ color: hasEstimate ? getRatingColor(predictedRating) : undefined }}>{hasEstimate ? predictedRating : '—'}</p></div>
      {delta != null && <div className="col-span-2 rounded-lg border border-zinc-800 bg-zinc-950/60 px-4 py-3 sm:col-span-1"><p className="mb-1 text-xs text-zinc-400">Diferença</p><p aria-label="Diferença de rating" className={`font-mono text-2xl font-bold tabular-nums ${delta === 0 ? 'text-emerald-400' : Math.abs(delta) <= 200 ? 'text-amber-300' : 'text-red-400'}`}>{delta > 0 ? '+' : delta < 0 ? '−' : ''}{Math.abs(delta)}</p><p className="mt-1 text-xs text-zinc-400">{direction}</p></div>}
    </div>
    {!hasReference && <p className="mt-3 text-xs text-zinc-400">Esta questão não possui rating oficial para comparar.</p>}
    {realTags.length > 0 && <div className="mt-4 flex flex-wrap items-center gap-1.5"><span className="mr-1 text-xs text-zinc-400">Tags oficiais</span>{realTags.map(tag => <span key={tag} className="rounded-md border border-zinc-700/60 bg-zinc-800/50 px-2 py-1 text-xs text-zinc-300">{tag}</span>)}</div>}
  </section>;
}
