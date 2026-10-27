import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layouts/PageLayout";
import { ContestCard, type ContestParticipation } from "@/components/contests/ContestCard";
import { ContestMetrics } from "@/components/contests/ContestMetrics";
import { ContestEvolution } from "@/components/contests/ContestEvolution";
import { ChevronLeft, ChevronRight, Search, Swords } from "lucide-react";

const KEY = "forja-contests-view-v1";
const defaults = { search: "", platform: "all", mode: "all", period: "all", sort: "recent", page: 1, scroll: 0 };
function readView() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(KEY) ?? "{}");
    return {
      search: typeof saved.search === "string" ? saved.search : "",
      platform: ["all", "CF_GYM", "CF_OFFICIAL"].includes(saved.platform) ? saved.platform as string : "all",
      mode: ["all", "virtual", "official"].includes(saved.mode) ? saved.mode as string : "all",
      period: ["all", "90", "365"].includes(saved.period) ? saved.period as string : "all",
      sort: ["recent", "oldest", "pending"].includes(saved.sort) ? saved.sort as string : "recent",
      page: Number.isInteger(saved.page) && saved.page > 0 ? saved.page as number : 1,
      scroll: Number.isFinite(saved.scroll) && saved.scroll > 0 ? saved.scroll as number : 0,
    };
  } catch { return defaults; }
}
function writeView(view: typeof defaults) {
  try { sessionStorage.setItem(KEY, JSON.stringify(view)); } catch { /* Navigation remains available without storage. */ }
}
function responsivePageSize() {
  if (typeof window.matchMedia !== "function") return 9;
  return window.matchMedia("(min-width: 1280px)").matches ? 9 : window.matchMedia("(min-width: 640px)").matches ? 6 : 3;
}
const selectClass = "rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2.5 text-xs text-zinc-300 outline-none focus-visible:ring-2 focus-visible:ring-forja";

export function Contests() {
  const [view, setView] = useState(readView);
  const [now] = useState(Date.now);
  const [pageSize, setPageSize] = useState(responsivePageSize);
  const restored = useRef(false);
  const { data: participations = [], isLoading, isError, refetch } = useQuery<ContestParticipation[]>({
    queryKey: ["contests"], queryFn: async () => (await api.get("/contests")).data,
  });
  useEffect(() => {
    const media = [window.matchMedia?.("(min-width: 1280px)"), window.matchMedia?.("(min-width: 640px)")];
    const resize = () => setPageSize(responsivePageSize());
    media.forEach(m => m?.addEventListener("change", resize));
    return () => media.forEach(m => m?.removeEventListener("change", resize));
  }, []);
  useEffect(() => { writeView(view); }, [view]);
  useEffect(() => {
    if (isLoading || restored.current) return;
    restored.current = true;
    const main = document.querySelector("main");
    if (main) main.scrollTop = view.scroll;
    // A standalone page (e.g. a preview) may use the window as its scroll container.
    else if (view.scroll > 0) window.scrollTo(0, view.scroll);
  }, [isLoading, view.scroll]);
  const update = (changes: Partial<typeof defaults>) => setView(current => ({ ...current, ...changes, page: 1, scroll: 0 }));
  const filtered = participations.filter(p => {
    if (view.platform !== "all" && p.contest_platform !== view.platform) return false;
    if (view.mode === "virtual" && !p.is_virtual || view.mode === "official" && p.is_virtual) return false;
    if (view.period !== "all" && (!p.participation_date || Date.parse(p.participation_date) < now - Number(view.period) * 86400000)) return false;
    return p.contest_name.toLocaleLowerCase().includes(view.search.toLocaleLowerCase());
  }).sort((a, b) => {
    const dates = (Date.parse(b.participation_date ?? "") || 0) - (Date.parse(a.participation_date ?? "") || 0);
    if (view.sort === "pending") return b.progress.pending_upsolve - a.progress.pending_upsolve || dates;
    return view.sort === "oldest" ? -dates : dates;
  });
  const pages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const page = Math.min(view.page, pages);
  const visible = filtered.slice((page - 1) * pageSize, page * pageSize);
  const recordScroll = () => writeView({ ...view, page, scroll: document.querySelector("main")?.scrollTop ?? window.scrollY });

  return <PageLayout topbarTitle="Contests" title="Meus Contests" description="Seu histórico de provas, o que evoluiu e o que ainda vale estudar.">
    {isLoading ? <p className="py-20 text-center text-sm text-white/55">Carregando contests...</p> : isError ? <div role="alert" className="rounded-xl border border-red-400/20 bg-red-400/5 p-5 text-sm text-red-300">
      Não foi possível carregar seus contests.<button onClick={() => refetch()} className="ml-2 underline">Tentar novamente</button>
    </div> : <>
      <div className="mb-6 flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          {[["all", "Todos"], ["CF_GYM", "Equipe"], ["CF_OFFICIAL", "Individual"]].map(([value, label]) => <button key={value} aria-pressed={view.platform === value} onClick={() => update({ platform: value })} className={`rounded-lg border px-4 py-2 text-xs font-semibold transition-colors ${view.platform === value ? "border-forja/40 bg-forja/10 text-red-300" : "border-zinc-800 text-zinc-500 hover:border-forja/30 hover:text-zinc-200"}`}>{label}</button>)}
        </div>
        <div className="flex flex-wrap gap-3">
          <label className="relative min-w-44 flex-1"><Search className="absolute left-3 top-3 size-3.5 text-white/35" /><input type="search" aria-label="Buscar contest" placeholder="Buscar contest..." value={view.search} onChange={e => update({ search: e.target.value })} className={`${selectClass} w-full pl-9`} /></label>
          <select aria-label="Tipo de participação" value={view.mode} onChange={e => update({ mode: e.target.value })} className={selectClass}><option value="all">Oficiais e virtuais</option><option value="virtual">Virtuais</option><option value="official">Oficiais</option></select>
          <select aria-label="Período" value={view.period} onChange={e => update({ period: e.target.value })} className={selectClass}><option value="all">Todo o histórico</option><option value="90">Últimos 90 dias</option><option value="365">Último ano</option></select>
          <select aria-label="Ordenar contests" value={view.sort} onChange={e => update({ sort: e.target.value })} className={selectClass}><option value="recent">Mais recentes</option><option value="oldest">Mais antigos</option><option value="pending">Mais questões para estudar</option></select>
        </div>
      </div>
      <ContestMetrics participations={filtered} />
      {!participations.length ? <div className="rounded-2xl border border-white/10 bg-white/[0.02] px-6 py-16 text-center"><Swords className="mx-auto mb-4 size-8 text-white/25" /><p className="font-medium text-white/80">Nenhum contest sincronizado</p><p className="mt-2 text-xs text-white/50">Sincronize sua conta para acompanhar seus treinos.</p></div> : <>
        <section aria-label="Histórico de contests">
          <div className="mb-3 flex items-center justify-between text-xs text-white/50"><span>{filtered.length} contests neste recorte</span></div>
          {visible.length ? <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">{visible.map(p => <ContestCard key={p.id} participation={p} onNavigate={recordScroll} />)}</div> : <div className="rounded-xl border border-dashed border-white/10 py-14 text-center"><p className="text-sm text-white/65">Nenhum contest neste recorte</p><button className="mt-3 text-xs text-sky-300 underline" onClick={() => setView(defaults)}>Limpar filtros</button></div>}
          <nav aria-label="Paginação de contests" className="mt-5 flex items-center justify-between gap-3">
            <p className="text-[11px] text-white/50">Página {page} de {pages}</p>
            <div className="flex gap-2"><button aria-label="Página anterior" disabled={page <= 1} onClick={() => setView(v => ({ ...v, page: page - 1 }))} className="rounded-lg border border-white/10 p-2 text-white/70 hover:bg-white/5 disabled:opacity-25"><ChevronLeft className="size-4" /></button>
              <button aria-label="Próxima página" disabled={page >= pages} onClick={() => setView(v => ({ ...v, page: page + 1 }))} className="rounded-lg border border-white/10 p-2 text-white/70 hover:bg-white/5 disabled:opacity-25"><ChevronRight className="size-4" /></button></div>
          </nav>
        </section>
        <ContestEvolution participations={filtered} />
      </>}
    </>}
  </PageLayout>;
}
