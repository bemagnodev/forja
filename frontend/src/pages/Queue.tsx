import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

import {
  DndContext, closestCenter,
  KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Inbox, AlertCircle } from "lucide-react";

import { PageLayout } from "@/components/layouts/PageLayout";
import { UndoToast } from "@/components/ui/undo-toast";

// Feature Components e configs
import type { QueueItem } from "@/components/queue/types";
import { SortableRow } from "@/components/queue/SortableRow";
import { AddItemDialog } from "@/components/queue/AddItemDialog";

export function Queue() {
  const queryClient = useQueryClient();

  const { data: items = [], isLoading, isError } = useQuery<QueueItem[]>({
    queryKey: ["queue"],
    queryFn: async () => {
      const { data } = await api.get("/queue");
      return data;
    },
  });

  const [undoToast, setUndoToast] = useState<{ id: number; title: string } | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_completed }: { id: number; is_completed: boolean }) =>
      api.post(`/queue/${id}/status`, { is_completed: !is_completed }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const handleToggle = useCallback(
    (id: number, currentStatus: boolean, title: string) => {
      // Atualização otimista: remove o item da lista visual instantaneamente
      queryClient.setQueryData(["queue"], (old: QueueItem[] | undefined) => {
        if (!old) return old;
        return old.map((item) => 
          item.id === id ? { ...item, is_completed: !currentStatus } : item
        );
      });

      toggleMutation.mutate({ id, is_completed: currentStatus });

      if (!currentStatus) {
        if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
        setUndoToast({ id, title });
        toastTimerRef.current = setTimeout(() => setUndoToast(null), 5500);
      } else {
        if (undoToast?.id === id) setUndoToast(null);
      }
    },
    [toggleMutation, undoToast, queryClient]
  );

  const handleUndo = () => {
    if (!undoToast) return;
    handleToggle(undoToast.id, true, undoToast.title);
    setUndoToast(null);
  };

  const patchMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) =>
      api.patch(`/queue/${id}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post("/queue", data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["queue"] }),
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedIds: number[]) =>
      api.post("/queue/reorder", { ordered_ids: orderedIds }),
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  );

  // Exibe apenas itens não concluídos
  const visibleItems = items.filter((i) => !i.is_completed);

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex  = items.findIndex((i) => i.id === over.id);
    const reordered = arrayMove(items, oldIndex, newIndex);
    queryClient.setQueryData(["queue"], reordered);
    reorderMutation.mutate(reordered.map((i) => i.id));
  };

  return (
    <PageLayout
      topbarTitle="Fila de Upsolving"
      title="Pendências"
      description="Organize seus próximos desafios e sessões de treinamento."
      action={<AddItemDialog onCreate={(data) => createMutation.mutate(data)} />}
    >
      {/* Toast de desfazer */}
      {undoToast && (
        <UndoToast
          title={undoToast.title}
          onUndo={handleUndo}
          onDismiss={() => setUndoToast(null)}
        />
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
          <div className="flex flex-col items-center gap-4">
            <div className="w-6 h-6 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <span className="text-[11px] text-white/25 font-medium tracking-widest uppercase">Carregando...</span>
          </div>
        </div>
      )}

      {/* Erro */}
      {isError && (
        <div className="rounded-2xl border flex items-center gap-4 border-red-500/20 bg-red-500/[0.04] p-5 text-red-400">
          <div className="w-8 h-8 rounded-full bg-red-500/10 border border-red-500/15 flex items-center justify-center shrink-0">
            <AlertCircle className="w-4 h-4" />
          </div>
          <div>
            <p className="font-bold text-[14px]">Conexão falhou</p>
            <p className="text-[12px] opacity-60 mt-0.5">Não foi possível conectar com o servidor. Django está rodando?</p>
          </div>
        </div>
      )}

      {/* ── Tabela ── */}
      {!isLoading && !isError && (
        <div className="border border-white/[0.07] rounded-2xl overflow-hidden bg-[#080808]/70 backdrop-blur-xl">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <Table>
              <colgroup>
                <col style={{ width: "52px" }} />
                <col style={{ width: "26%" }} />
                <col style={{ width: "76px" }} />
                <col style={{ width: "26%" }} />
                <col />
                <col style={{ width: "116px" }} />
              </colgroup>

              <TableHeader>
                <TableRow className="border-b border-white/[0.07] bg-black/35 hover:bg-black/35">
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 pl-5 pr-2">
                    {/* Vazio — check + grip */}
                  </TableHead>
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 px-3">
                    Questão / Estudo
                  </TableHead>
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 px-3 text-center">
                    Rating
                  </TableHead>
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 px-3">
                    Tags
                  </TableHead>
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 px-3">
                    Descrição
                  </TableHead>
                  <TableHead className="text-[9px] uppercase tracking-widest text-white/20 font-bold py-3 px-4 text-center">
                    Prioridade
                  </TableHead>
                </TableRow>
              </TableHeader>

              <TableBody>
                {/* Estado vazio */}
                {visibleItems.length === 0 && (
                  <TableRow className="hover:bg-transparent border-0">
                    <TableCell colSpan={6} className="py-32 text-center">
                      <div className="flex flex-col items-center gap-4">
                        <div className="w-12 h-12 rounded-full bg-white/[0.03] border border-white/[0.06] flex items-center justify-center text-white/20">
                          <Inbox className="w-6 h-6" strokeWidth={1.5} />
                        </div>
                        <div>
                          <p className="text-[14px] font-bold text-white/70">A fila está vazia.</p>
                          <p className="text-[12px] text-white/40 mt-0.5">Sua dívida técnica foi completamente paga! 🎉</p>
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}

                <SortableContext items={visibleItems.map((i) => i.id)} strategy={verticalListSortingStrategy}>
                  {visibleItems.map((item) => (
                    <SortableRow
                      key={item.id}
                      item={item}
                      onToggle={handleToggle}
                      onPatchPriority={(id, priority) => patchMutation.mutate({ id, data: { priority } })}
                      onPatchDescription={(id, description) => patchMutation.mutate({ id, data: { description } })}
                    />
                  ))}
                </SortableContext>
              </TableBody>
            </Table>
          </DndContext>
        </div>
      )}
    </PageLayout>
  );
}
