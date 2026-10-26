import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Menu, X } from 'lucide-react';

/** The desktop sidebar becomes a dismissible drawer on narrow screens. */
export function AppFrame({ sidebar, children }: { sidebar: ReactNode; children: ReactNode }) {
  const [open, setOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const drawer = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const media = window.matchMedia?.('(min-width: 640px)');
    const resize = () => { if (media?.matches) setOpen(false); };
    media?.addEventListener('change', resize);
    return () => media?.removeEventListener('change', resize);
  }, []);
  useEffect(() => {
    if (!open) return;
    drawer.current?.querySelector<HTMLElement>('a, button')?.focus();
    const keyboard = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setOpen(false); toggle.current?.focus(); }
      if (event.key === 'Tab') {
        const targets = drawer.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled])');
        if (!targets?.length) return;
        const first = targets[0], last = targets[targets.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    };
    document.addEventListener('keydown', keyboard);
    return () => document.removeEventListener('keydown', keyboard);
  }, [open]);
  return <div className="flex h-screen w-full flex-col overflow-hidden bg-[#050505] text-foreground">
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 bg-[#080808] px-4 sm:hidden">
      <span className="text-sm font-bold text-white/90">Forja</span>
      <button ref={toggle} aria-label={open ? 'Fechar menu' : 'Abrir menu'} aria-expanded={open} aria-controls="app-navigation" onClick={() => setOpen(v => !v)} className="rounded-lg p-2 text-white/75 focus-visible:outline focus-visible:outline-sky-400">{open ? <X className="size-5" /> : <Menu className="size-5" />}</button>
    </header>
    <div className="flex min-h-0 flex-1">
      {open && <button aria-label="Fechar navegação" onClick={() => { setOpen(false); toggle.current?.focus(); }} className="fixed inset-0 z-40 bg-black/60 sm:hidden" />}
      <div ref={drawer} id="app-navigation" onClick={event => { if ((event.target as Element).closest('a')) setOpen(false); }} className={`${open ? 'block' : 'hidden'} fixed inset-y-0 left-0 z-50 overflow-y-auto sm:static sm:block sm:shrink-0`}>
        {sidebar}
      </div>
      <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto" inert={open || undefined}>{children}</main>
    </div>
  </div>;
}
