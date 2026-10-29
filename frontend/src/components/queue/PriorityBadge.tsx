import { priorityConfig } from "./constants";

export function PriorityBadge({ priority }: { priority: string }) {
  const c = priorityConfig[priority];
  if (!c) return null;
  const Icon = c.Icon;
  return (
    <span
      className="inline-flex items-center justify-center gap-1.5 min-h-6 text-[11px] font-medium px-2 py-0.5 rounded-md border whitespace-nowrap"
      style={{
        color:            c.text,
        backgroundColor:  "rgba(255,255,255,0.025)",
        borderColor:      c.border + "35",
      }}
    >
      {Icon && <Icon className="w-2.5 h-2.5 shrink-0" strokeWidth={2.5} />}
      {priority === "FUTURE" ? "Futuro" : priority === "UPSOLVING" ? "Upsolving" : priority}
    </span>
  );
}
