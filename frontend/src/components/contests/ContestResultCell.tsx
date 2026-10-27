import { useId, useState } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import type { ContestResult } from './types';

function formatContestTime(seconds: number | null | undefined) {
  if (seconds == null || !Number.isFinite(seconds) || seconds < 0) return '—';
  const minutes = Math.floor(seconds / 60);
  return `${Math.floor(minutes / 60).toString().padStart(2, '0')}:${(minutes % 60).toString().padStart(2, '0')}`;
}

function Breakdown({ values }: { values: Record<string, number> }) {
  const entries = Object.entries(values).filter(([, count]) => count > 0);
  return <p className="tabular-nums text-white/80">{entries.map(([key, count]) => `${key}: ${count}`).join(' · ') || 'Nenhum erro de julgamento'}</p>;
}

export function ContestResultCell({ result, systemStatus, label = '' }: {
  result?: ContestResult | null; systemStatus?: string; label?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const accepted = result ? result.accepted : (systemStatus === 'SOLVED_LIVE' ? true : null);
  const partial = !result || result.coverage !== 'complete';
  const attempts = result?.failed_attempts;
  const sign = accepted === true ? `+${attempts == null ? '?' : attempts || ''}`
    : accepted === false ? `−${attempts == null ? '?' : attempts || ''}` : '?';
  const time = formatContestTime(result?.first_ac_seconds);
  const upsolved = result?.is_upsolved ?? systemStatus === 'UPSOLVED';
  const description = accepted ? 'AC no contest' : accepted === false ? 'Sem AC no contest' : 'Resultado parcial';
  const upsolveDescription = !result ? 'Resolução posterior indicada pelo acompanhamento; dados de submissão indisponíveis'
    : result.manual_completion ? 'Conclusão manual; sem AC confirmado'
    : result.upsolved_at ? `AC depois da prova · ${new Date(result.upsolved_at).toLocaleString('pt-BR')}`
    : 'AC importado; relação temporal com a prova não confirmada';

  return <div className="flex min-w-16 items-center justify-center">
    <Tooltip open={open} onOpenChange={setOpen} triggerId={id}>
      <TooltipTrigger id={id} closeOnClick={false} onClick={() => setOpen(true)} aria-label={`${label ? `${label}: ` : ''}${description}${attempts != null ? `, ${attempts} ${attempts === 1 ? 'erro' : 'erros'}` : ''}${accepted ? `, ${time}` : ''}${upsolved ? ', Upsolvada' : ''}`}
        className="flex min-h-11 min-w-14 items-center justify-center gap-1.5 rounded-lg px-1.5 py-1 transition-colors hover:bg-white/[0.04] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forja">
        <span className="flex flex-col items-center"><span className={`text-[15px] font-bold leading-5 tabular-nums ${accepted ? 'text-emerald-400' : accepted === false ? 'text-sky-400' : 'text-white/40'}`}>{sign}</span>
        {accepted && <span className="text-[10px] font-medium leading-4 tabular-nums text-white/55">{time}</span>}</span>
        {upsolved && <span title="Upsolvada" className="rounded border border-sky-400/20 bg-sky-400/[0.06] px-1 py-0.5 text-[8px] font-bold tracking-wide text-sky-300"><span aria-hidden="true">UP</span><span className="sr-only">Upsolvada</span></span>}
      </TooltipTrigger>
      <TooltipContent role="tooltip" className="block max-w-72 space-y-2 rounded-xl border border-white/10 bg-[#17191f] p-3 text-left text-xs leading-relaxed text-white shadow-xl">
        <p className="font-semibold">{label && `${label} · `}{description}</p>
        {partial && <p className="text-amber-300">Dados parciais. Tempos ou tentativas podem estar indisponíveis.</p>}
        {accepted && <p>Primeiro AC: {time} desde o início da prova.</p>}
        <div><p className="mb-0.5 text-white/50">{accepted ? 'Antes do AC' : 'Durante a prova'}</p><Breakdown values={result?.errors_before_ac ?? {}} /></div>
        {Object.keys(result?.errors_after_ac ?? {}).length > 0 && <div><p className="mb-0.5 text-white/50">Depois do AC</p><Breakdown values={result!.errors_after_ac} /></div>}
        {!!result?.compilation_errors && <p>CE: {result.compilation_errors} · fora do contador</p>}
        {upsolved && <p className="border-t border-white/10 pt-2 text-sky-300">{upsolveDescription}</p>}
      </TooltipContent>
    </Tooltip>
  </div>;
}
