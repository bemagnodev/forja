import { useState, useRef } from "react";
import { Pencil } from "lucide-react";
import { Input } from "@/components/ui/input";

export function EditableDescription({ value, onSave, disabled = false }: {
  value: string | null; onSave: (text: string) => Promise<void>; disabled?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value ?? '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(false);
  const saving = useRef(false);
  const save = async () => {
    if (saving.current) return;
    if (text.trim() === (value ?? '')) { setEditing(false); return; }
    saving.current = true; setPending(true); setError(false);
    try { await onSave(text.trim()); setEditing(false); }
    catch { setError(true); }
    finally { saving.current = false; setPending(false); }
  };
  return editing ? <div>
    <Input autoFocus aria-label="Editar descrição" value={text} disabled={pending} onChange={e => setText(e.target.value)}
      onBlur={() => { if (!error) void save(); }}
      onKeyDown={e => {
        if (e.key === 'Enter') { e.preventDefault(); void save(); }
        if (e.key === 'Escape' && !pending) { setEditing(false); setError(false); }
      }} placeholder="Escreva uma descrição..." className="h-8 w-full text-xs text-white/80 caret-white bg-black/40 border-white/15 placeholder:text-white/25" />
    {error && <p role="alert" className="text-xs text-red-400">Não foi salvo. Enter para tentar novamente.</p>}
  </div> : <button disabled={disabled} onClick={() => { setText(value ?? ''); setEditing(true); }}
    aria-label={value ? "Editar descrição" : "Adicionar descrição"} title={value || "Adicionar descrição"}
    className={`group/description text-left flex items-center gap-2 w-full min-w-0 text-xs hover:text-white/80 disabled:opacity-50 ${value ? 'text-white/50' : 'text-white/25'}`}>
    <span className="truncate">{value || '—'}</span>
    {!value && <Pencil aria-hidden="true" className="h-3 w-3 shrink-0 opacity-60 group-hover/description:opacity-100 group-focus-visible/description:opacity-100" />}
  </button>;
}
