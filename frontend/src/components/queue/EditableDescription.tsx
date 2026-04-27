import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";

export function EditableDescription({
  value,
  onSave,
}: {
  value: string | null;
  onSave: (text: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(value ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const handleSave = () => {
    setEditing(false);
    if (text.trim() !== (value ?? "")) onSave(text.trim());
  };

  if (editing) {
    return (
      <Input
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={handleSave}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSave();
          if (e.key === "Escape") { setText(value ?? ""); setEditing(false); }
        }}
        className="h-7 w-full bg-black/40 border border-white/15 text-[12px] text-white/80 focus-visible:ring-1 focus-visible:ring-primary/30 px-2 shadow-inner rounded-md"
        placeholder="Adicione uma nota..."
      />
    );
  }

  return (
    <div
      onClick={() => setEditing(true)}
      className="group/desc relative w-full cursor-pointer py-1 px-2 -ml-2 rounded border border-transparent hover:bg-white/[0.04] hover:border-white/[0.08] transition-colors"
    >
      <p
        className="text-[12px] text-white/35 group-hover/desc:text-white/55 truncate w-full min-h-[20px]"
        title={value || "Clique para adicionar nota"}
      >
        {value || ""}
      </p>
    </div>
  );
}
