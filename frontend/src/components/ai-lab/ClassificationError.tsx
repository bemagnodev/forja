import { useState } from 'react';
import { classificationErrorInfo } from '@/lib/classification-error';

export function ClassificationError({ error }: { error: unknown }) {
  const [copied, setCopied] = useState('');
  const info = classificationErrorInfo(error);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify({ message: info.message, ...info.diagnostic }, null, 2));
      setCopied('Diagnóstico copiado.');
    } catch { setCopied('Não foi possível copiar. Selecione os detalhes manualmente.'); }
  };
  const labels: Record<string, string> = { stage: 'Etapa', code: 'Código', model: 'Modelo',
    platform: 'Plataforma', upstream_status: 'HTTP de origem', request_id: 'Identificador',
    source_category: 'Evidência do bloqueio', source_server: 'Servidor de origem', source_cf_ray: 'Cloudflare Ray ID' };
  return <div role="alert" className="rounded-xl border border-red-500/25 bg-red-500/5 p-5 text-sm">
    <h3 className="font-semibold text-red-300">{info.title}</h3>
    <p className="mt-2 text-zinc-300">{info.message}</p>
    {Object.keys(info.diagnostic).length > 0 && <details className="mt-4 text-xs text-zinc-400">
      <summary className="w-fit cursor-pointer rounded focus-visible:ring-2 focus-visible:ring-primary">Detalhes técnicos</summary>
      <dl className="my-3 grid gap-2">{Object.entries(info.diagnostic).map(([key, value]) =>
        <div key={key} className="flex flex-wrap gap-x-2"><dt>{labels[key]}:</dt><dd className="break-all font-mono text-zinc-300">{value}</dd></div>)}</dl>
      <button type="button" onClick={() => void copy()} className="rounded border border-zinc-700 px-3 py-2 text-zinc-200 focus-visible:ring-2 focus-visible:ring-primary">Copiar diagnóstico</button>
      <span role="status" className="ml-3">{copied}</span>
    </details>}
  </div>;
}
