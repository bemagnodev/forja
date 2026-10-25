import { useId, useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { GripVertical, Sparkles } from "lucide-react";
import { TableRow, TableCell } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { QueueItem } from "./types";
import { priorityConfig, priorityOptions } from "./constants";
import { PlatformIcon } from "./PlatformIcon";
import { PriorityBadge } from "./PriorityBadge";
import { EditableDescription } from "./EditableDescription";
import { getRatingColor } from "@/lib/ratings";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast-context";
import { classificationErrorInfo } from "@/lib/classification-error";
import { hasNativeRating, NATIVE_RATING_MESSAGE } from "@/lib/product-classification";

function RatingBadge({ rating, isAi = false }: { rating: number | null; isAi?: boolean }) {
  if (rating == null) return <span className="text-[11px] text-white/18 font-mono select-none">—</span>;

  const colorStyle = { color: getRatingColor(rating) };

  return (
    <div className="flex items-center justify-center gap-1.5" title={isAi ? "Rating estimado por IA" : undefined}>
      {isAi && <Sparkles className="w-3 h-3 text-fuchsia-400 opacity-80" />}
      <span 
        className="text-[16px] font-mono tracking-tighter font-black"
        style={colorStyle}
      >
        {rating}
      </span>
    </div>
  );
}

/**
 * Abrevia nomes de contest para no máximo ~8 caracteres.
 * Estrategia: pega as iniciais das palavras + números relevantes.
 * Ex: "AtCoder Beginner Contest 457" => "ABC457"
 *     "CCPC 2024 Final"              => "CCPC24"
 *     "Codeforces Round 950"         => "CF950"
 */
function abbreviateContest(name: string): string {
  if (!name) return "";

  // Extrai apenas os números do nome (anos, números de rodada, etc.)
  const digits = name.match(/\d+/g)?.join("") ?? "";

  // Palavras que não contribuem para a sigla (stop words)
  const stopWords = new Set(["contest", "the", "and", "for", "of", "round", "div", "edition", "final", "beginner", "intermediate"]);

  // Pega a inicial maiúscula de cada palavra relevante
  const initials = name
    .split(/\s+/)
    .filter((w) => !stopWords.has(w.toLowerCase()) && /[a-zA-Z]/.test(w))
    .map((w) => w[0].toUpperCase())
    .join("");

  // Concatena sigla + números, limitando ao total de 7 chars
  const abbr = (initials + digits).slice(0, 7);
  return abbr || name.slice(0, 7);
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
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [nativeNoticeFor, setNativeNoticeFor] = useState<number | null>(null);
  const noticeId = useId();
  const showNativeNotice = item.linked_problem_id != null && nativeNoticeFor === item.linked_problem_id;

  const predictMutation = useMutation({
    mutationFn: async ({ force }: { force?: boolean } = {}) => {
      if (!item.linked_problem_id) throw new Error("Sem problema vinculado");
      const start = performance.now();
      const { data } = await api.post(`/problems/${item.linked_problem_id}/predict`, null, {
        params: { force: force ? "true" : "false" }
      });
      return { data, time: performance.now() - start };
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      queryClient.invalidateQueries({ queryKey: ["contest-problems"] });
      toast({
        title: "Classificação concluída!",
        description: `Predição gerada em ${(result.time / 1000).toFixed(1)} segundos.`,
        type: "success",
      });
    },
    onError: (error) => {
      const info = classificationErrorInfo(error);
      if (info.diagnostic.code === 'native_rating_available') {
        setNativeNoticeFor(item.linked_problem_id ?? null);
        queryClient.invalidateQueries({ queryKey: ['queue'] });
        queryClient.invalidateQueries({ queryKey: ['contest-problems'] });
        return;
      }
      toast({
        title: info.title,
        description: info.toastMessage,
        type: "error",
      });
    }
  });

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
        <div className="flex items-center gap-2.5 w-full">
          <PlatformIcon platform={item.source_platform} type={item.item_type} />
          
          <div className="flex items-center gap-2 min-w-0 flex-1">
            {/* 
              Preferência de título:
              1. problem_title: título real do modelo Problem (ex: "Two Sum" para AtCoder)
              2. item.title sem o prefixo platform_id (padrão legado para CF/CSES)
              3. item.title puro como fallback final
            */}
            {(() => {
              const displayTitle = item.problem_title
                ?? (item.platform_id && item.title.startsWith(`${item.platform_id} - `)
                    ? item.title.replace(`${item.platform_id} - `, "")
                    : item.title);
              return item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[13px] font-medium text-white/80 hover:text-sky-400 hover:underline transition-colors truncate leading-snug"
                >
                  {displayTitle}
                </a>
              ) : (
                <span className="text-[13px] font-medium text-white/80 group-hover:text-white transition-colors truncate leading-snug">
                  {displayTitle}
                </span>
              );
            })()}

            {item.already_solved && (
              <div
                className="shrink-0 flex items-center justify-center px-1.5 py-0.5 rounded-sm bg-emerald-500/10 border border-emerald-500/20 shadow-[0_0_8px_rgba(16,185,129,0.15)]"
                title="Já resolvido"
              >
                <span className="text-emerald-500 text-[9px] font-black tracking-widest leading-none mt-[1px]">AC</span>
              </div>
            )}
            
            {item.linked_problem_id && (
              <div className="ml-auto shrink-0">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (hasNativeRating(item.rating) || showNativeNotice) {
                      setNativeNoticeFor(item.linked_problem_id ?? null);
                      return;
                    }
                    predictMutation.mutate({ force: e.shiftKey });
                  }}
                  disabled={predictMutation.isPending}
                  title={hasNativeRating(item.rating) || showNativeNotice
                    ? 'Esta questão já possui rating nativo da plataforma'
                    : 'Estimar rating e tags com IA (Shift+Click para forçar recálculo)'}
                  aria-label="Estimar rating e tags com IA"
                  aria-describedby={showNativeNotice ? noticeId : undefined}
                  className="w-6 h-6 flex items-center justify-center rounded-lg border border-fuchsia-400/20 bg-fuchsia-400/10 text-fuchsia-400 hover:bg-fuchsia-400/20 transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-fuchsia-400 disabled:opacity-40"
                >
                  {predictMutation.isPending ? (
                    <div className="w-3 h-3 border-2 border-fuchsia-400/30 border-t-fuchsia-400 rounded-full animate-spin" />
                  ) : (
                    <Sparkles className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            )}
          </div>
        </div>
        {showNativeNotice && <p id={noticeId} role="status" className="mt-1.5 max-w-sm whitespace-normal text-[11px] leading-relaxed text-white/50">
          {NATIVE_RATING_MESSAGE}
        </p>}
      </TableCell>

      {/* ── RATING ── */}
      <TableCell className="py-3.5 px-3 align-middle text-center">
        <RatingBadge rating={item.rating ?? item.ai_rating ?? null} isAi={!hasNativeRating(item.rating) && item.ai_rating != null} />
      </TableCell>

      {/* ── TAGS ── */}
      <TableCell className="py-2 px-3 align-middle overflow-hidden">
        {(item.tags?.length > 0 || item.ai_tags?.length) ? (
          <Tooltip>
            <TooltipTrigger className="flex items-center gap-1 cursor-help w-full overflow-hidden">
                {!item.tags?.length && item.ai_tags && item.ai_tags.length > 0 && (
                  <Sparkles className="w-3 h-3 text-fuchsia-400 opacity-80 shrink-0" />
                )}
                {(item.tags?.length > 0 ? item.tags : item.ai_tags || []).slice(0, 2).map((tag) => (
                  <span
                    key={tag}
                    className={`shrink truncate min-w-0 text-[10px] px-1.5 py-[2.5px] rounded uppercase tracking-wider font-bold border transition-colors ${
                      !item.tags?.length && item.ai_tags && item.ai_tags.length > 0 
                      ? "bg-fuchsia-500/10 border-fuchsia-500/20 text-fuchsia-300"
                      : "bg-white/[0.06] border-white/[0.08] text-white/55"
                    }`}
                  >
                    {tag}
                  </span>
                ))}
                {(item.tags?.length > 0 ? item.tags : item.ai_tags || []).length > 2 && (
                  <span className="shrink-0 text-[9px] px-1.5 py-[2px] rounded bg-white/[0.03] text-white/35 font-bold border border-white/[0.06]">
                    +{(item.tags?.length > 0 ? item.tags : item.ai_tags || []).length - 2}
                  </span>
                )}
            </TooltipTrigger>
            <TooltipContent 
              side="top" 
              align="start"
              className="bg-[#121212] border-white/10 text-white/70 shadow-2xl px-3 py-2.5 flex flex-wrap gap-1.5 max-w-[320px]"
            >
              {(item.tags?.length > 0 ? item.tags : item.ai_tags || []).map(tag => (
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

      {/* ── CONTEST ── */}
      <TableCell className="py-3.5 px-3 align-middle">
        {item.contest_name ? (
          <Tooltip>
            <TooltipTrigger className="text-[11px] font-mono font-bold tracking-wider text-white/35 hover:text-white/60 transition-colors cursor-default uppercase">
                {abbreviateContest(item.contest_name)}
            </TooltipTrigger>
            <TooltipContent
              side="top"
              align="start"
              className="bg-[#121212] border-white/10 text-white/70 shadow-2xl px-3 py-2 text-[12px] max-w-[240px]"
            >
              {item.contest_name}
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
          <DropdownMenuTrigger className="focus:outline-none cursor-pointer hover:scale-[1.03] transition-all active:scale-95">
            <PriorityBadge priority={item.priority} />
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
