import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { ListPlus, Sparkles } from "lucide-react";
import type { ContestProblem } from "./types";

interface ProblemActionsCellProps {
  problem: ContestProblem;
}

export function ProblemActionsCell({ problem }: ProblemActionsCellProps) {
  const queryClient = useQueryClient();
  const [toastMsg, setToastMsg] = useState<string | null>(null);

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
      // Invalida a fila para refletir o novo item
      queryClient.invalidateQueries({ queryKey: ["queue"] });
      setToastMsg("Adicionado à fila!");
      setTimeout(() => setToastMsg(null), 2500);
    },
  });

  return (
    <div className="flex items-center justify-end gap-1 relative opacity-40 group-hover/row:opacity-100 transition-all duration-200">
      {/* Toast inline discreto */}
      {toastMsg && (
        <span className="absolute -top-7 right-0 text-[10px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-2 py-0.5 whitespace-nowrap pointer-events-none z-10">
          {toastMsg}
        </span>
      )}

      {/* Botão de IA */}
      <button
        title="Em breve: Estimar rating e tags com IA"
        className="w-8 h-8 flex items-center justify-center rounded-lg text-fuchsia-400/70 hover:text-fuchsia-400 hover:bg-fuchsia-400/10 hover:shadow-[0_0_15px_rgba(232,121,249,0.2)] transition-all"
      >
        <Sparkles className="w-4 h-4" />
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
