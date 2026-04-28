import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical } from "lucide-react";
import { TableRow, TableCell } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { QueueItem } from "./types";
import { priorityConfig, priorityOptions } from "./constants";
import { PlatformIcon } from "./PlatformIcon";
import { PriorityBadge } from "./PriorityBadge";
import { EditableDescription } from "./EditableDescription";

// Lê o valor resolvido da variável CSS do DOM em runtime
function getCssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function getRatingColor(rating?: number): string {
  if (!rating) return "";
  if (rating < 1200) return getCssVar("--rating-gray");
  if (rating < 1400) return getCssVar("--rating-green");
  if (rating < 1600) return getCssVar("--rating-cyan");
  if (rating < 1900) return getCssVar("--rating-blue");
  if (rating < 2100) return getCssVar("--rating-violet");
  if (rating < 2300) return getCssVar("--rating-orange");
  if (rating < 2400) return getCssVar("--rating-orange");
  return getCssVar("--rating-red");
}

export function SortableRow({
  item,
  onToggle,
  onPatchPriority,
  onPatchDescription,
}: {
  item: QueueItem;
  onToggle: (id: number, currentStatus: boolean, title: string) => void;
  onPatchPriority: (id: number, priority: string) => void;
  onPatchDescription: (id: number, description: string) => void;
}) {
  const {
    attributes, listeners, setNodeRef,
    transform, transition, isDragging,
  } = useSortable({ id: item.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    ...(isDragging ? { position: "relative" as const, zIndex: 50, opacity: 0.8 } : {}),
  };

  const pc = priorityConfig[item.priority];

  // Acento lateral via box-shadow inset — usa opacity na borda se necessário
  const rowStyle = {
    ...style,
    boxShadow: `inset 2px 0 0 ${pc?.border ?? "transparent"}`,
  };

  return (
    <TableRow
      ref={setNodeRef}
      style={rowStyle}
      className="border-b border-white/[0.05] transition-colors duration-150 group relative hover:bg-white/[0.025] bg-transparent"
    >
      {/* ── CHECK: grip + checkbox ── */}
      <TableCell className="py-0 pl-5 pr-2 align-middle">
        <div className="flex items-center gap-2 h-full py-3.5">
          <button
            {...attributes}
            {...listeners}
            tabIndex={-1}
            className="cursor-grab active:cursor-grabbing p-0.5 text-white/[0.12] hover:text-white/30 transition-colors focus:outline-none"
          >
            <GripVertical className="w-3.5 h-3.5" />
          </button>
          <div onClick={(e) => e.stopPropagation()}>
            <Checkbox
              checked={item.is_completed}
              onCheckedChange={() => onToggle(item.id, item.is_completed, item.title)}
              className="border-white/15 hover:border-white/30 transition-all duration-200"
            />
          </div>
        </div>
      </TableCell>

      {/* ── QUESTÃO / ESTUDO ── */}
      <TableCell className="py-3.5 px-3 align-middle">
        <div className="flex items-center gap-2.5">
          <PlatformIcon platform={item.source_platform} type={item.item_type} />
          
          <div className="flex items-center gap-2 min-w-0">
            {item.url ? (
              <a 
                href={item.url} 
                target="_blank" 
                rel="noopener noreferrer"
                className="text-[13px] font-medium text-white/80 hover:text-sky-400 hover:underline transition-colors truncate leading-snug"
              >
                {item.platform_id && item.title.startsWith(`${item.platform_id} - `) 
                  ? item.title.replace(`${item.platform_id} - `, "") 
                  : item.title}
              </a>
            ) : (
              <span className="text-[13px] font-medium text-white/80 group-hover:text-white transition-colors truncate leading-snug">
                {item.platform_id && item.title.startsWith(`${item.platform_id} - `) 
                  ? item.title.replace(`${item.platform_id} - `, "") 
                  : item.title}
              </span>
            )}

            {item.already_solved && (
              <div 
                className="shrink-0 flex items-center justify-center px-1.5 py-0.5 rounded-sm bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.15)]"
                title="Já resolvido"
              >
                <span className="text-emerald-500 text-[9px] font-black tracking-widest leading-none mt-[1px]">AC</span>
              </div>
            )}
          </div>
        </div>
      </TableCell>

      {/* ── RATING ── */}
      <TableCell className="py-3.5 px-3 align-middle text-center">
        {item.rating ? (
          <span 
            className="text-[16px] font-mono tracking-tighter font-black"
            style={{ color: getRatingColor(item.rating) }}
          >
            {item.rating}
          </span>
        ) : (
          <span className="text-[11px] text-white/18 font-mono select-none">—</span>
        )}
      </TableCell>

      {/* ── TAGS ── */}
      {/* overflow:hidden impede que tags longas invadam colunas vizinhas */}
      <TableCell className="py-2 px-3 align-middle overflow-hidden">
        {item.tags?.length > 0 ? (
          <Tooltip>
            <TooltipTrigger asChild>
              {/* container flex que não cresce além da célula */}
              <div className="flex items-center gap-1 cursor-help w-full overflow-hidden">
                {item.tags.slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className="shrink truncate min-w-0 text-[10px] px-1.5 py-[2.5px] rounded bg-white/[0.06] text-white/55 uppercase tracking-wider font-bold border border-white/[0.08]"
                  >
                    {tag}
                  </span>
                ))}
                {item.tags.length > 2 && (
                  <span className="shrink-0 text-[9px] px-1.5 py-[2px] rounded bg-white/[0.03] text-white/35 font-bold border border-white/[0.06]">
                    +{item.tags.length - 2}
                  </span>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent 
              side="top" 
              align="start"
              className="bg-[#121212] border-white/10 text-white/70 shadow-2xl px-3 py-2.5 flex flex-wrap gap-1.5 max-w-[320px]"
            >
              {item.tags.map(tag => (
                <span key={tag} className="uppercase text-[10px] font-semibold tracking-widest bg-white/[0.06] px-2 py-1 rounded border border-white/[0.08]">
                  {tag}
                </span>
              ))}
            </TooltipContent>
          </Tooltip>
        ) : (
          <span className="text-[11px] text-white/18 select-none">—</span>
        )}
      </TableCell>

      {/* ── DESCRIÇÃO ── */}
      <TableCell className="py-3.5 px-3 align-middle">
        <EditableDescription
          value={item.description}
          onSave={(text) => onPatchDescription(item.id, text)}
        />
      </TableCell>

      {/* ── PRIORIDADE ── */}
      <TableCell className="py-3.5 px-4 align-middle text-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="focus:outline-none cursor-pointer hover:scale-[1.03] transition-all active:scale-95">
              <PriorityBadge priority={item.priority} />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            className="bg-[#0d0d0d]/98 backdrop-blur-xl border-white/[0.09] min-w-[168px] shadow-xl p-1 rounded-xl"
          >
            {priorityOptions.map((opt) => (
              <DropdownMenuItem
                key={opt.value}
                onClick={() => onPatchPriority(item.id, opt.value)}
                className="text-[12px] text-white/55 focus:text-white hover:text-white focus:bg-white/10 hover:bg-white/10 cursor-pointer gap-2.5 py-2 px-3 rounded-lg transition-colors font-medium outline-none"
              >
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: opt.color }}
                />
                {opt.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}
