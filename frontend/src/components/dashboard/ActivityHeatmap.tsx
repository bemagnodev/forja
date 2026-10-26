import type { HeatmapData } from "@/lib/api-dashboard";

export function ActivityHeatmap({ data, referenceDate }: { data: HeatmapData[]; referenceDate: string }) {
  // Date-only calculations use UTC arithmetic, anchored to the backend's local date.
  const end = new Date(`${referenceDate}T00:00:00Z`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(referenceDate) || Number.isNaN(end.getTime())) {
    return <section aria-label="Calendário anual" className="rounded-xl border border-zinc-800 p-5 text-sm text-zinc-400">
      Calendário indisponível. Atualize os dados para tentar novamente.
    </section>;
  }
  const start = new Date(end); start.setUTCDate(end.getUTCDate() - 364);
  const dataMap = new Map(data.map(d => [d.date, d.count]));
  const days = Array.from({ length: 365 }, (_, i) => {
    const date = new Date(start); date.setUTCDate(start.getUTCDate() + i);
    const key = date.toISOString().slice(0, 10);
    return { date, key, count: dataMap.get(key) ?? 0 };
  });
  const leading = start.getUTCDay();
  const trailing = (7 - (leading + 365) % 7) % 7;
  const columns = (leading + 365 + trailing) / 7;
  const months = days.filter((day, i) => day.date.getUTCDate() === 1 || i === 0);
  const color = (count: number) => count === 0 ? 'bg-zinc-800/60' : count < 3 ? 'bg-red-950' : count < 6 ? 'bg-red-800' : count < 10 ? 'bg-red-600' : 'bg-red-500';
  return <section className="min-w-0 bg-zinc-900/50 border border-zinc-800 rounded-xl p-5" aria-label="Calendário anual">
    <div className="flex flex-wrap gap-2 justify-between items-center mb-5">
      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">ATIVIDADE — ÚLTIMO ANO</h3>
      <span className="text-xs text-zinc-400">{days.filter(d => d.count > 0).length} dias ativos</span>
    </div>
    <div className="relative h-6 ml-8 text-[10px] text-zinc-400" aria-hidden="true">
      {months.map(day => <span key={day.key} className="absolute" style={{ left: `${Math.floor((leading + days.indexOf(day)) / 7) / columns * 100}%` }}>
        {day.date.toLocaleDateString('pt-BR', { month: 'short', timeZone: 'UTC' }).replace('.', '')}
      </span>)}
    </div>
    <div role="img" aria-label="Atividade de submissões aceitas nos últimos 365 dias"
      className="grid gap-[2px] w-full items-center"
      style={{ gridTemplateColumns: `24px repeat(${columns}, minmax(0, 1fr))`, gridTemplateRows: 'repeat(7, minmax(0, 1fr))' }}>
      {['Dom', '', 'Ter', '', 'Qui', '', 'Sáb'].map((day, i) => <span key={`label-${i}`} aria-hidden="true"
        className="text-[9px] leading-none text-zinc-500" style={{ gridColumn: 1, gridRow: i + 1 }}>{day}</span>)}
      {Array.from({ length: leading + 365 + trailing }, (_, position) => {
        const day = days[position - leading];
        const style = { gridRow: position % 7 + 1, gridColumn: Math.floor(position / 7) + 2 };
        return day ? <div key={day.key} style={style} className={`w-full aspect-square rounded-[2px] ${color(day.count)}`} title={`${day.key}: ${day.count} submissões aceitas`} />
          : <span key={`padding-${position}`} style={style} data-calendar-padding aria-hidden="true" />;
      })}
    </div>
    <div className="flex justify-end items-center gap-1 mt-4 text-[10px] text-zinc-400">
      <span>Menos</span>{[0, 1, 3, 6, 10].map(n => <span key={n} className={`w-2.5 h-2.5 rounded-sm ${color(n)}`} />)}<span>Mais</span>
    </div>
  </section>;
}
