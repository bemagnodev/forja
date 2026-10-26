import { useState, useRef } from "react";
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
      }} className="h-8 w-full text-xs" />
    {error && <p role="alert" className="text-xs text-red-400">Não foi salvo. Enter para tentar novamente.</p>}
  </div> : <button disabled={disabled} onClick={() => { setText(value ?? ''); setEditing(true); }}
    aria-label="Editar descrição" title={value || 'Adicionar nota'}
    className="text-left block w-full truncate text-xs text-white/50 hover:text-white/80 disabled:opacity-50">
    {value || 'Adicionar nota'}
  </button>;
}
