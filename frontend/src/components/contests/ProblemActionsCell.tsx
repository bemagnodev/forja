import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ListPlus, Sparkles } from "lucide-react";
import type { ContestProblem } from "./types";
import { useToast } from "@/components/ui/toast-context";

interface ProblemActionsCellProps {
  problem: ContestProblem;
}

export function ProblemActionsCell({ problem }: ProblemActionsCellProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const addToQueueMutation = useMutation({
    mutationFn: () =>
      api.post("/queue", {
        title: problem.title,
        item_type: "PROBLEM",
        priority: "UPSOLVING",
        source_platform: "CODEFORCES",
        linked_problem_id: problem.id,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      
      toast({
        title: "Adicionado à fila!",
        description: `O problema "${problem.title}" está pronto para upsolving.`,
        type: "success",
      });
    },
  });

  const predictMutation = useMutation({
    mutationFn: async ({ force }: { force?: boolean } = {}) => {
      const start = performance.now();
      const { data } = await api.post(`/problems/${problem.id}/predict`, null, {
        params: { force: force ? "true" : "false" }
      });
      return { data, time: performance.now() - start };
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["contest-problems"] });
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      
      toast({
        title: "Classificação concluída!",
        description: `Predição gerada para "${problem.title}" em ${(result.time / 1000).toFixed(1)} segundos.`,
        type: "success",
      });
    },
    onError: () => {
      toast({
        title: "Erro na predição",
        description: "A IA não conseguiu classificar este problema. Pode ser um erro no formato do enunciado.",
        type: "error",
      });
    }
  });

  return (
    <div className="flex items-center justify-end gap-1 relative opacity-40 group-hover/row:opacity-100 transition-all duration-200">

      {/* Botão de IA */}
      <button
        onClick={(e) => predictMutation.mutate({ force: e.shiftKey })}
        disabled={predictMutation.isPending}
        title="Estimar rating e tags com IA (Shift+Click para forçar recálculo)"
        aria-label="Estimar rating e tags com IA"
        className="w-8 h-8 flex items-center justify-center rounded-lg text-fuchsia-400/70 hover:text-fuchsia-400 hover:bg-fuchsia-400/10 hover:shadow-[0_0_15px_rgba(232,121,249,0.2)] transition-all disabled:opacity-40"
      >
        {predictMutation.isPending ? (
          <div className="w-4 h-4 border-2 border-fuchsia-400/30 border-t-fuchsia-400 rounded-full animate-spin" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
      </button>

      {/* Adicionar à fila */}
      <button
        onClick={() => addToQueueMutation.mutate()}
        disabled={addToQueueMutation.isPending}
        title="Adicionar à Fila (Upsolving)"
        className="w-8 h-8 flex items-center justify-center rounded-lg text-white/30 hover:text-[#dc143c] hover:bg-[#dc143c]/10 hover:shadow-[0_0_15px_rgba(220,20,60,0.15)] transition-all disabled:opacity-40"
      >
        <ListPlus className="w-4 h-4" />
      </button>
    </div>
  );
}
