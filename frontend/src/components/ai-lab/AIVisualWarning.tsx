import { ImageOff } from "lucide-react";

export function AIVisualWarning() {
  return <div role="note" className="mt-4 flex min-w-0 items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-left text-xs leading-relaxed text-amber-200">
    <ImageOff aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
    <span className="min-w-0 break-words">Esta questão contém imagens que não foram analisadas; a estimativa pode ser menos precisa.</span>
  </div>;
}
