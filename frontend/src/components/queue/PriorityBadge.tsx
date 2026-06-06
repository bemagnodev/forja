import { priorityConfig } from "./constants";

export function PriorityBadge({ priority }: { priority: string }) {
  const c = priorityConfig[priority];
  if (!c) return null;
  const Icon = c.Icon;
  return (
    <span
      className="inline-flex items-center justify-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded-md border whitespace-nowrap"
      style={{
        color:            c.text,
        backgroundColor:  c.bg,
        borderColor:      c.border + "60",
      }}
    >
      {Icon && <Icon className="w-2.5 h-2.5 shrink-0" strokeWidth={2.5} />}
      {priority === "FUTURE" ? "FUTURO" : priority}
    </span>
  );
}
