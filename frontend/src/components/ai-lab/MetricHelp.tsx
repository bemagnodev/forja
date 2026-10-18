import { useId, useState } from "react";
import { Info } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";

export function MetricHelp({ label, children }: { label: string; children: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return <Tooltip open={open} triggerId={id} onOpenChange={(next, details) => { if (details.reason !== "trigger-press") setOpen(next); }}>
    <TooltipTrigger id={id} aria-label={`Ajuda: ${label}`} onClick={() => setOpen(true)} className="inline-flex items-center gap-1.5 rounded py-1 text-xs font-medium text-zinc-400 outline-none hover:text-zinc-100 focus-visible:ring-2 focus-visible:ring-primary">
      {label}<Info className="size-3 text-zinc-600" />
    </TooltipTrigger>
    <TooltipContent role="tooltip" className="max-w-xs border border-zinc-700 bg-zinc-900 text-zinc-200">{children}</TooltipContent>
  </Tooltip>;
}
