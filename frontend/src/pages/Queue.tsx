import React, { useCallback, useState, useMemo, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

import {
  DndContext, closestCenter,
  KeyboardSensor, PointerSensor, useSensor, useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy, arrayMove } from "@dnd-kit/sortable";

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Inbox, AlertCircle, RefreshCw } from "lucide-react";

import { PageLayout } from "@/components/layouts/PageLayout";
import { useToast } from "@/components/ui/toast-context";

// Feature Components e configs
import type { QueueItem, QueueCreateInput } from "@/components/queue/types";
import { SortableRow } from "@/components/queue/SortableRow";
import { AddItemDialog } from "@/components/queue/AddItemDialog";

export function Queue() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data: items = [], isLoading, isError } = useQuery<QueueItem[]>({
    queryKey: ["queue"],
    queryFn: async () => {
      const { data } = await api.get("/queue");
      return data;
    },
  });

  const busy = useRef(false);
  const toggleMutation = useMutation({
    mutationFn: ({ id, is_completed }: { id: number; is_completed: boolean }) =>
      api.post(`/queue/${id}/status`, { is_completed: !is_completed }),
  });
  const handleToggle = useCallback(async function toggleQueueItem(id: number, currentStatus: boolean, title: string) {
    if (busy.current) return;
    busy.current = true;
    try {
      await toggleMutation.mutateAsync({ id, is_completed: currentStatus });
      await queryClient.cancelQueries({ queryKey: ['queue'] });
      queryClient.setQueryData<QueueItem[]>(['queue'], old => old?.map(item => item.id === id ? { ...item, is_completed: !currentStatus } : item));
      if (!currentStatus) toast({ title: 'Item finalizado', description: title, type: 'success', action: {
        label: 'Desfazer', icon: <RefreshCw className="w-3 h-3" />,
        onClick: () => { void toggleQueueItem(id, true, title); },
      } });
    } catch {
      toast({ title: 'Não foi possível salvar', description: 'O estado anterior foi preservado. Tente novamente.', type: 'error' });
    } finally {
      busy.current = false;
      void queryClient.invalidateQueries({ queryKey: ['queue'] });
    }
  }, [toggleMutation, queryClient, toast]);

  const patchMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Record<string, unknown> }) => api.patch(`/queue/${id}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue'] }),
    onError: () => toast({ title: 'Não foi possível salvar a edição', description: 'Tente novamente.', type: 'error' }),
  });
  const createMutation = useMutation({
    mutationFn: (data: QueueCreateInput) => api.post('/queue', data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue'] }),
  });
  const reorderMutation = useMutation({
    mutationFn: (orderedIds: number[]) => api.post('/queue/reorder', { ordered_ids: orderedIds }),
    onMutate: async orderedIds => {
      await queryClient.cancelQueries({ queryKey: ['queue'] });
      const previous = queryClient.getQueryData<QueueItem[]>(['queue']);
      const reordered = orderedIds.map(id => previous?.find(item => item.id === id)).filter((item): item is QueueItem => !!item);
      queryClient.setQueryData(['queue'], reordered);
      return { previous, reordered };
    },
    onError: (_error, _ids, context) => {
      // Do not overwrite a newer refetch with an older snapshot.
      if (context && queryClient.getQueryData(['queue']) === context.reordered) queryClient.setQueryData(['queue'], context.previous);
      toast({ title: 'Não foi possível salvar a ordem', description: 'A fila será atualizada novamente.', type: 'error' });
    },
    onSettled: () => { busy.current = false; return queryClient.invalidateQueries({ queryKey: ['queue'] }); },
  });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor)
  );

  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [groupByContest, setGroupByContest] = useState(false);

  // Exibe apenas itens não concluídos e aplica filtro de prioridade
  const filteredItems = useMemo(() => {
    return items.filter((i) => {
      if (i.is_completed) return false;
      if (priorityFilter !== "ALL" && i.priority !== priorityFilter) return false;
      return true;
    });
  }, [items, priorityFilter]);

  const groupedItems = useMemo(() => {
    if (!groupByContest) return null;
    const groups: Record<string, QueueItem[]> = {};
    filteredItems.forEach(i => {
      const key = i.contest_name || "Sem Contest";
      if (!groups[key]) groups[key] = [];
      groups[key].push(i);
    });
    return groups;
  }, [filteredItems, groupByContest]);

  const handleDragEnd = (event: DragEndEvent) => {
    if (groupByContest || busy.current || patchMutation.isPending) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = items.findIndex((i) => i.id === active.id);
    const newIndex  = items.findIndex((i) => i.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const reordered = arrayMove(items, oldIndex, newIndex);
    busy.current = true;
    reorderMutation.mutate(reordered.map((i) => i.id));
  };

  return (
    <PageLayout
      topbarTitle="Fila de Upsolving"
      title="Fila"
      description="Organize suas questões e sessões de treinamento"
      action={<AddItemDialog onCreate={(data) => createMutation.mutateAsync(data)} />}
    >

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
            <p className="text-[12px] opacity-60 mt-0.5">Não foi possível conectar com o servidor. Tente novamente em instantes.</p>
          </div>
        </div>
      )}

      {/* Filters and Controls */}
      {!isLoading && !isError && (
        <div className="flex items-center justify-between mb-4 mt-2">
          <div className="flex gap-2">
            {["ALL", "P0", "P1", "P2", "UPSOLVING", "FUTURE"].map(p => (
              <button
                key={p}
                onClick={() => setPriorityFilter(p)}
                className={`px-3 py-1 rounded-full text-[11px] font-bold tracking-wider transition-colors border ${priorityFilter === p ? "bg-[#dc143c]/20 text-[#dc143c] border-[#dc143c]" : "bg-white/5 text-white/40 border-white/10 hover:bg-white/10"}`}
              >
                {p === "ALL" ? "TODAS" : p}
              </button>
            ))}
          </div>
          
          <label className="flex items-center gap-2 cursor-pointer">
            <span className="text-[11px] font-bold tracking-wider text-white/50 uppercase select-none">Agrupar por Contest</span>
            <div className={`w-8 h-4 rounded-full transition-colors relative ${groupByContest ? 'bg-[#dc143c]' : 'bg-white/10'}`}>
              <div className={`absolute top-0.5 left-0.5 w-3 h-3 bg-white rounded-full transition-transform ${groupByContest ? 'translate-x-4' : 'translate-x-0'}`} />
            </div>
            <input type="checkbox" className="sr-only" checked={groupByContest} onChange={(e) => setGroupByContest(e.target.checked)} />
          </label>
        </div>
      )}

      {/* ── Tabela ── */}
      {!isLoading && !isError && (
        <div className="border border-white/[0.07] rounded-2xl overflow-hidden bg-[#080808]/70 backdrop-blur-xl">
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <Table className="table-fixed">
              <colgroup>
                <col style={{ width: '64px' }} /><col style={{ width: '27%' }} />
                <col style={{ width: '110px' }} /><col style={{ width: '76px' }} />
                <col style={{ width: '22%' }} /><col style={{ width: '84px' }} /><col />
              </colgroup>
              <TableHeader><TableRow className="bg-black/35 border-b border-white/[0.07]">
                {['', 'Questão / Estudo', 'Prioridade', 'Rating', 'Tags', 'Contest', 'Descrição'].map((label, i) => <TableHead key={i} className="px-3 py-3 text-[10px] uppercase tracking-wide text-white/50">{label}</TableHead>)}
              </TableRow></TableHeader>

              <TableBody>
                {/* Estado vazio */}
                {filteredItems.length === 0 && (
                  <TableRow className="hover:bg-transparent border-0">
                    <TableCell colSpan={7} className="py-32 text-center">
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

                {groupByContest ? (
                  Object.entries(groupedItems!).map(([contestName, contestItems]) => (
                    <React.Fragment key={contestName}>
                      <TableRow className="bg-white/[0.02] border-y border-white/[0.05] hover:bg-white/[0.02]">
                        <TableCell colSpan={7} className="py-2.5 px-5 font-bold text-[12px] text-white/50 uppercase tracking-widest">
                          {contestName}
                        </TableCell>
                      </TableRow>
                      <SortableContext items={contestItems.map((i) => i.id)} strategy={verticalListSortingStrategy}>
                        {contestItems.map((item) => (
                          <SortableRow
                            key={item.id}
                            item={item}
                            disabled={toggleMutation.isPending || reorderMutation.isPending || patchMutation.isPending}
                            onToggle={handleToggle}
                            onPatchPriority={(id, priority) => patchMutation.mutate({ id, data: { priority } })}
                            onPatchDescription={async (id, description) => { await patchMutation.mutateAsync({ id, data: { description } }); }}
                          />
                        ))}
                      </SortableContext>
                    </React.Fragment>
                  ))
                ) : (
                  <SortableContext items={filteredItems.map((i) => i.id)} strategy={verticalListSortingStrategy}>
                    {filteredItems.map((item) => (
                      <SortableRow
                        key={item.id}
                        item={item}
                            disabled={toggleMutation.isPending || reorderMutation.isPending || patchMutation.isPending}
                        onToggle={handleToggle}
                        onPatchPriority={(id, priority) => patchMutation.mutate({ id, data: { priority } })}
                        onPatchDescription={async (id, description) => { await patchMutation.mutateAsync({ id, data: { description } }); }}
                      />
                    ))}
                  </SortableContext>
                )}
              </TableBody>
            </Table>
          </DndContext>
        </div>
      )}
    </PageLayout>
  );
}
