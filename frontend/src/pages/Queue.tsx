import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import {
  Table, TableBody, TableCell,
  TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog, DialogContent, DialogHeader,
  DialogTitle, DialogTrigger, DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select, SelectContent, SelectItem,
  SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SiCodeforces } from "react-icons/si";
import { Inbox, Plus, GripVertical, BookOpen, Search } from "lucide-react";

// dnd-kit
import {
  DndContext, closestCenter,
  KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

// ─── Tipos ──────────────────────────────────────────────
interface QueueItem {
  id: number;
  item_type: "PROBLEM" | "STUDY_SESSION";
  title: string;
  description: string | null;
  source_platform: string | null;
  priority: "P0" | "P1" | "P2" | "UPSOLVING";
  status: string;
  done: boolean;
  order: number;
  created_at: string;
}

interface ProblemResult {
  id: number;
  platform_id: string;
  title: string;
  platform: string;
}

// ─── Constantes Visuais ─────────────────────────────────
// Borda lateral esquerda por prioridade
const priorityBorderColor: Record<string, string> = {
  P0:        "#dc143c",   // Crimson (Forja)
  P1:        "#f97316",   // Orange
  P2:        "#eab308",   // Yellow
  UPSOLVING: "#581c87",   // Dark Purple
};

const priorityBadge: Record<string, string> = {
  P0:        "text-[#dc143c] border-[#dc143c]/30 bg-[#dc143c]/10",
  P1:        "text-orange-400 border-orange-500/30 bg-orange-500/10",
  P2:        "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
  UPSOLVING: "text-purple-400 border-purple-500/30 bg-purple-500/10",
};

const priorityOptions = [
  { value: "P0", label: "P0 — Crítico", color: "#dc143c" },
  { value: "P1", label: "P1 — Alto", color: "#f97316" },
  { value: "P2", label: "P2 — Normal", color: "#eab308" },
  { value: "UPSOLVING", label: "Upsolving", color: "#581c87" },
];

// ─── Ícone de Plataforma (compacto, para uso ao lado do título) ────
function PlatformIcon({ platform, size = "sm" }: { platform: string | null; size?: "sm" | "md" }) {
  const s = size === "sm" ? "h-3.5" : "h-5";
  
  if (!platform) return null;

  const logos: Record<string, string> = {
    CODEFORCES: "/platforms/codeforces.png",
    ATCODER:    "/platforms/atcoder.png",
    CSES:       "/platforms/cses.jpg",
  };

  const src = logos[platform];
  if (!src) return <span className="text-[10px] text-white/40">{platform}</span>;

  return (
    <div className={`${size === "sm" ? "w-4" : "w-6"} flex items-center justify-center shrink-0`}>
      <img 
        src={src} 
        alt={platform} 
        className={`${s} object-contain`}
        title={platform}
      />
    </div>
  );
}

// ─── Descrição editável inline ──────────────────────────
function EditableDescription({
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
    if (text !== (value ?? "")) onSave(text);
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={handleSave}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSave();
          if (e.key === "Escape") { setText(value ?? ""); setEditing(false); }
        }}
        className="w-full bg-transparent border-b border-white/20 focus:border-[#dc143c]/50 text-[12px] text-white/50 outline-none py-0.5 placeholder:text-white/15"
        placeholder="Adicionar nota..."
      />
    );
  }

  return (
    <button
      onClick={() => setEditing(true)}
      className="text-[12px] text-white/25 hover:text-white/50 transition-colors truncate max-w-[200px] text-left"
      title={value || "Clique para editar"}
    >
      {value || "—"}
    </button>
  );
}

// ─── Linha Sorteável ─────────────────────────────────────
function SortableRow({
  item,
  onToggle,
  onPatchPriority,
  onPatchDescription,
}: {
  item: QueueItem;
  onToggle: (id: number) => void;
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
    opacity: isDragging ? 0.4 : 1,
    borderLeft: `3px solid ${priorityBorderColor[item.priority] ?? "transparent"}`,
  };

  const icon = <PlatformIcon platform={item.source_platform} />;

  return (
    <TableRow
      ref={setNodeRef}
      style={style}
      className={`border-b border-white/5 hover:bg-white/[0.02] transition-all group ${
        item.done ? "opacity-35" : ""
      }`}
    >
      {/* Grip */}
      <TableCell className="w-8 py-2.5 px-1">
        <button
          {...attributes}
          {...listeners}
          className="cursor-grab active:cursor-grabbing p-1 rounded hover:bg-white/10 transition-colors"
          tabIndex={-1}
        >
          <GripVertical className="w-3.5 h-3.5 text-white/15 group-hover:text-white/30 transition-colors" />
        </button>
      </TableCell>

      {/* Checkbox */}
      <TableCell className="w-10 py-2.5">
        <Checkbox
          checked={item.done}
          onCheckedChange={() => onToggle(item.id)}
          className="border-white/20 data-[state=checked]:bg-[#dc143c] data-[state=checked]:border-[#dc143c]"
        />
      </TableCell>

      {/* Questão / Estudo — com ícone de plataforma */}
      <TableCell className="py-2.5">
        <div className="flex items-center gap-2">
          {icon}
          <span
            className={`text-[13px] font-medium transition-colors ${
              item.done
                ? "line-through text-white/20"
                : "text-white/80 group-hover:text-white"
            }`}
          >
            {item.title}
          </span>
        </div>
      </TableCell>

      {/* Descrição — editável inline */}
      <TableCell className="py-2.5 w-52">
        <EditableDescription
          value={item.description}
          onSave={(text) => onPatchDescription(item.id, text)}
        />
      </TableCell>

      {/* Prioridade — dropdown editável */}
      <TableCell className="py-2.5 w-32">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="cursor-pointer focus:outline-none">
              <Badge
                variant="outline"
                className={`text-[10px] uppercase font-bold tracking-wider py-0.5 cursor-pointer hover:opacity-80 ${priorityBadge[item.priority]}`}
              >
                {item.priority}
              </Badge>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="bg-[#111] border-white/10 min-w-[150px]">
            {priorityOptions.map((opt) => (
              <DropdownMenuItem
                key={opt.value}
                onClick={() => onPatchPriority(item.id, opt.value)}
                className="text-[12px] text-white/70 hover:text-white focus:text-white cursor-pointer gap-2"
              >
                <span style={{ color: opt.color }}>●</span>
                {opt.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </TableCell>
    </TableRow>
  );
}

// ─── Modal de criação ───────────────────────────────────
function AddItemDialog({ 
  onCreate 
}: { 
  onCreate: (data: any) => void 
}) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [itemType, setItemType] = useState("PROBLEM");
  const [priority, setPriority] = useState("P2");
  const [platform, setPlatform] = useState<string | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProblem, setSelectedProblem] = useState<ProblemResult | null>(null);
  const [open, setOpen] = useState(false);

  // Busca de problemas no banco
  const { data: searchResults = [] } = useQuery<ProblemResult[]>({
    queryKey: ["problem-search", searchQuery, platform],
    queryFn: async () => {
      if (!searchQuery || searchQuery.length < 2) return [];
      const params = new URLSearchParams({ q: searchQuery, limit: "8" });
      if (platform) params.set("platform", platform);
      const { data } = await api.get(`/problems/search?${params}`);
      return data;
    },
    enabled: searchQuery.length >= 2 && itemType === "PROBLEM",
  });

  const resetForm = () => {
    setTitle("");
    setDescription("");
    setPriority("P2");
    setItemType("PROBLEM");
    setPlatform(undefined);
    setSearchQuery("");
    setSelectedProblem(null);
  };

  const handleSubmit = () => {
    const finalTitle = selectedProblem
      ? `${selectedProblem.platform_id} - ${selectedProblem.title}`
      : title.trim();
    if (!finalTitle) return;

    onCreate({
      title: finalTitle,
      description: description.trim() || null,
      item_type: itemType,
      priority,
      source_platform: itemType === "PROBLEM" ? platform : null,
      linked_problem_id: selectedProblem?.id ?? null,
    });
    setOpen(false);
    resetForm();
  };

  const selectProblem = (p: ProblemResult) => {
    setSelectedProblem(p);
    setTitle(`${p.platform_id} - ${p.title}`);
    setSearchQuery("");
  };

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetForm(); }}>
      <DialogTrigger
        render={
          <Button
            size="sm"
            className="bg-[#dc143c] hover:bg-[#b01030] text-white text-[12px] font-semibold gap-1.5 h-8 px-4"
          >
            <Plus className="w-3.5 h-3.5" />
            Adicionar
          </Button>
        }
      />
      <DialogContent className="bg-[#0a0a0a] border border-[#dc143c]/30 text-white sm:max-w-lg shadow-[0_0_40px_rgba(220,20,60,0.15)]">
        <DialogHeader>
          <DialogTitle className="text-white text-base font-bold tracking-tight">
            ⚔️ Nova Tarefa na Forja
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5 py-3">
          {/* Tipo — botões toggle */}
          <div className="space-y-2">
            <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">Tipo</label>
            <div className="flex gap-2">
              <button
                onClick={() => { setItemType("PROBLEM"); setSelectedProblem(null); }}
                className={`flex-1 py-2 rounded-md text-[12px] font-semibold border transition-all ${
                  itemType === "PROBLEM"
                    ? "bg-[#dc143c]/15 border-[#dc143c]/40 text-white"
                    : "bg-white/5 border-white/10 text-white/40 hover:text-white/60"
                }`}
              >
                📋 Questão
              </button>
              <button
                onClick={() => { setItemType("STUDY_SESSION"); setSelectedProblem(null); setPlatform(undefined); }}
                className={`flex-1 py-2 rounded-md text-[12px] font-semibold border transition-all ${
                  itemType === "STUDY_SESSION"
                    ? "bg-purple-500/15 border-purple-500/40 text-white"
                    : "bg-white/5 border-white/10 text-white/40 hover:text-white/60"
                }`}
              >
                <BookOpen className="w-3.5 h-3.5 inline mr-1 -mt-0.5" /> Sessão de Estudo
              </button>
            </div>
          </div>

          {/* Se PROBLEM: plataforma + busca */}
          {itemType === "PROBLEM" && (
            <>
              {/* Plataforma — botões com ícone */}
              <div className="space-y-2">
                <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">Plataforma</label>
                <div className="flex gap-2">
                  {[
                    { value: "CODEFORCES", label: "Codeforces" },
                    { value: "ATCODER", label: "AtCoder" },
                    { value: "CSES", label: "CSES" },
                  ].map((p) => (
                    <button
                      key={p.value}
                      onClick={() => { setPlatform(p.value); setSelectedProblem(null); }}
                      className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-[12px] font-medium border transition-all ${
                        platform === p.value
                          ? "bg-white/10 border-white/25 text-white"
                          : "bg-white/3 border-white/8 text-white/35 hover:text-white/60 hover:border-white/15"
                      }`}
                    >
                      <PlatformIcon platform={p.value} />
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Busca de problema no banco */}
              <div className="space-y-2">
                <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">
                  Buscar Questão
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20" />
                  <Input
                    value={selectedProblem ? `${selectedProblem.platform_id} - ${selectedProblem.title}` : searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setSelectedProblem(null);
                    }}
                    placeholder="Busque por ID ou nome (ex: 1A, Theatre)"
                    className="pl-9 bg-white/5 border-white/10 text-white placeholder:text-white/20"
                  />
                </div>

                {/* Resultados da busca */}
                {searchResults.length > 0 && !selectedProblem && (
                  <div className="border border-white/10 rounded-md max-h-40 overflow-y-auto bg-[#111]">
                    {searchResults.map((p) => (
                      <button
                        key={p.id}
                        onClick={() => selectProblem(p)}
                        className="w-full px-3 py-2 text-left text-[12px] hover:bg-white/5 transition-colors flex items-center gap-2 border-b border-white/5 last:border-0"
                      >
                        <PlatformIcon platform={p.platform} />
                        <span className="text-white/50 font-mono">{p.platform_id}</span>
                        <span className="text-white/70 truncate">{p.title}</span>
                      </button>
                    ))}
                  </div>
                )}

                {/* Ou título manual */}
                {!selectedProblem && searchQuery.length < 2 && (
                  <Input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Ou digite manualmente: 1A - Theatre Square"
                    className="bg-white/5 border-white/10 text-white placeholder:text-white/15 text-[12px]"
                  />
                )}
              </div>
            </>
          )}

          {/* Se STUDY_SESSION: apenas título */}
          {itemType === "STUDY_SESSION" && (
            <div className="space-y-2">
              <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">
                Objetivo do Estudo
              </label>
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex: Estudar DP em árvores, Segment Tree lazy"
                className="bg-white/5 border-white/10 text-white placeholder:text-white/20"
              />
            </div>
          )}

          {/* Prioridade — sempre */}
          <div className="space-y-2">
            <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">Prioridade</label>
            <div className="flex gap-2">
              {priorityOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setPriority(opt.value)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-md text-[12px] font-medium border transition-all ${
                    priority === opt.value
                      ? "bg-white/10 border-white/25 text-white"
                      : "bg-white/3 border-white/8 text-white/35 hover:text-white/50"
                  }`}
                >
                  <span style={{ color: opt.color }}>●</span>
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Descrição — sempre */}
          <div className="space-y-2">
            <label className="text-[11px] uppercase text-white/40 font-semibold tracking-wider">
              Descrição <span className="text-white/20">(opcional)</span>
            </label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ex: Focar em DP com bitmask, revisar editorial"
              className="bg-white/5 border-white/10 text-white placeholder:text-white/15"
            />
          </div>
        </div>

        <DialogFooter>
          <DialogClose
            render={
              <Button variant="ghost" className="text-white/50 hover:text-white hover:bg-white/5" size="sm">
                Cancelar
              </Button>
            }
          />
          <Button
            onClick={handleSubmit}
            disabled={(!title.trim() && !selectedProblem)}
            size="sm"
            className="bg-[#dc143c] hover:bg-[#b01030] text-white font-bold px-6"
          >
            ⚔️ Criar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Página Principal ───────────────────────────────────
export function Queue() {
  const queryClient = useQueryClient();

  const { data: items = [], isLoading, isError } = useQuery<QueueItem[]>({
    queryKey: ["queue"],
    queryFn: async () => {
      const { data } = await api.get("/queue");
      return data;
    },
  });

  // Mutations
  const toggleMutation = useMutation({
    mutationFn: (id: number) => api.post(`/queue/${id}/toggle`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.patch(`/queue/${id}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedIds: number[]) =>
      api.post("/queue/reorder", { ordered_ids: orderedIds }),
  });

  // Sensores dnd-kit
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex = items.findIndex((i) => i.id === over.id);
    const reordered = arrayMove(items, oldIndex, newIndex);
    queryClient.setQueryData(["queue"], reordered);
    reorderMutation.mutate(reordered.map((i) => i.id));
  };

  // Colunas da tabela (sem Origem, com Descrição)
  const colCount = 5; // grip + checkbox + titulo + desc + prioridade

  return (
    <div className="flex flex-col min-h-screen">
      {/* Topbar */}
      <header className="h-14 border-b border-white/10 flex items-center px-8">
        <h1 className="text-[13px] font-semibold text-white/50 tracking-wide uppercase">
          Fila de Upsolving
        </h1>
      </header>

      {/* Conteúdo */}
      <div className="flex-1 p-8 max-w-6xl">
        {/* Título + Botão Adicionar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">
              Sua Dívida Técnica
            </h2>
            <p className="text-[13px] text-white/40 mt-0.5">
              Arraste para reordenar. Clique na prioridade para alterar.
            </p>
          </div>
          <AddItemDialog onCreate={(data) => createMutation.mutate(data)} />
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="text-[13px] text-white/30 py-10 animate-pulse">
            Carregando a fila...
          </div>
        )}

        {/* Erro */}
        {isError && (
          <div className="rounded-md border border-[#dc143c]/30 bg-[#dc143c]/5 px-4 py-3 text-[13px] text-[#dc143c]">
            Falha ao conectar com o backend. O Django está rodando em :8000?
          </div>
        )}

        {/* Tabela */}
        {!isLoading && !isError && (
          <div className="border border-[#dc143c]/20 rounded-lg overflow-hidden shadow-[0_0_20px_rgba(220,20,60,0.05)]">
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-[#dc143c]/15 bg-[#dc143c]/[0.02] hover:bg-[#dc143c]/[0.02]">
                    <TableHead className="w-8 py-2.5" />
                    <TableHead className="text-[10px] uppercase tracking-widest text-[#dc143c]/50 font-bold w-10 py-2.5">
                      ✓
                    </TableHead>
                    <TableHead className="text-[10px] uppercase tracking-widest text-[#dc143c]/50 font-bold py-2.5">
                      Questão / Estudo
                    </TableHead>
                    <TableHead className="text-[10px] uppercase tracking-widest text-[#dc143c]/50 font-bold w-52 py-2.5">
                      Descrição
                    </TableHead>
                    <TableHead className="text-[10px] uppercase tracking-widest text-[#dc143c]/50 font-bold w-32 py-2.5">
                      Prioridade
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.length === 0 && (
                    <TableRow className="hover:bg-transparent border-0">
                      <TableCell colSpan={colCount} className="py-20 text-center">
                        <div className="flex flex-col items-center gap-3 text-white/20">
                          <Inbox className="w-8 h-8" strokeWidth={1} />
                          <p className="text-[13px]">
                            A forja está vazia — clique em "Adicionar" para começar.
                          </p>
                        </div>
                      </TableCell>
                    </TableRow>
                  )}
                  <SortableContext
                    items={items.map((i) => i.id)}
                    strategy={verticalListSortingStrategy}
                  >
                    {items.map((item) => (
                      <SortableRow
                        key={item.id}
                        item={item}
                        onToggle={(id) => toggleMutation.mutate(id)}
                        onPatchPriority={(id, priority) =>
                          patchMutation.mutate({ id, data: { priority } })
                        }
                        onPatchDescription={(id, description) =>
                          patchMutation.mutate({ id, data: { description } })
                        }
                      />
                    ))}
                  </SortableContext>
                </TableBody>
              </Table>
            </DndContext>
          </div>
        )}
      </div>
    </div>
  );
}
