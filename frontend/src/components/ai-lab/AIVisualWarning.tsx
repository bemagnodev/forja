import { ImageOff } from "lucide-react";

export function AIVisualWarning() {
  return <span role="note" className="mt-2 inline-flex w-56 max-w-64 items-start gap-1.5 whitespace-normal text-left text-[10px] leading-relaxed text-amber-300/90">
    <ImageOff aria-hidden="true" className="mt-0.5 size-3 shrink-0" />
    <span>Esta questão contém imagens que não foram analisadas; a estimativa pode ser menos precisa.</span>
  </span>;
}
