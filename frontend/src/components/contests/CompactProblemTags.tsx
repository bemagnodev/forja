import { useId, useState } from 'react';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

export function CompactProblemTags({ tags }: { tags: string[] }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  if (!tags.length) return null;
  return <Tooltip open={open} onOpenChange={setOpen} triggerId={id}>
    <TooltipTrigger id={id} closeOnClick={false} onClick={() => setOpen(true)} aria-label="Todas as tags"
      className="flex min-w-0 max-w-56 items-center gap-1 overflow-hidden rounded py-1 text-left focus-visible:outline focus-visible:outline-forja">
      {tags.slice(0, 2).map(tag => <span key={tag} className="min-w-0 truncate rounded border border-white/[0.07] bg-white/[0.035] px-1.5 py-0.5 text-[10px] text-zinc-400">{tag}</span>)}
      {tags.length > 2 && <span className="shrink-0 text-[10px] text-zinc-500">+{tags.length - 2}</span>}
    </TooltipTrigger>
    <TooltipContent role="tooltip" className="flex max-w-72 flex-wrap gap-1.5 border border-zinc-800 bg-[#121212] p-3 text-zinc-300">
      {tags.map(tag => <span key={tag} className="rounded border border-zinc-800 px-1.5 py-1 text-[10px]">{tag}</span>)}
    </TooltipContent>
  </Tooltip>;
}
