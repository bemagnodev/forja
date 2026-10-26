import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/ui/toast-context";
import { api } from "@/lib/api";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

// Status disponíveis para triagem manual do usuário
const STATUS_OPTIONS = [
  { value: "PENDING_TRIAGE", label: "Pendente",  dot: "#ffffff40", bg: "bg-white/5", text: "text-white/40", border: "border-white/10" },
  { value: "DOABLE",         label: "Dá pra fazer", dot: "#fbbf24", bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/20" },
  { value: "DONE",           label: "Concluído", dot: "#34d399", bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/20" },
  { value: "FUTURE",         label: "Futuro",    dot: "#c084fc", bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/20" },
  { value: "IGNORED",        label: "Ignorada",  dot: "#ffffff26", bg: "bg-white/5", text: "text-white/30", border: "border-white/10" },
] as const;

interface ProblemStatusSelectProps {
  problemId: number;
  trackingId: number | null;
  currentStatus: string;
  contestId: number;
}

export function ProblemStatusSelect({
  problemId,
  currentStatus,
  contestId,
}: ProblemStatusSelectProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const mutation = useMutation({
    mutationFn: (review_status: string) =>
      api.patch(`/tracking/${problemId}`, { review_status }),
    onError: () => toast({ title: "Não foi possível salvar o status", description: "O status anterior foi preservado.", type: "error" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contest-problems", contestId] });
      queryClient.invalidateQueries({ queryKey: ['contest', contestId] });
      for (const key of ['contests', 'dashboard', 'queue']) queryClient.invalidateQueries({ queryKey: [key] });
    },
  });

  const current = STATUS_OPTIONS.find(s => s.value === currentStatus) ?? STATUS_OPTIONS[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
          disabled={mutation.isPending}
          className={`inline-flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded-md border whitespace-nowrap cursor-pointer hover:scale-[1.03] transition-all active:scale-95 disabled:opacity-50 disabled:cursor-wait ${current.bg} ${current.text} ${current.border} focus:outline-none`}
      >
          <span 
            className="w-2 h-2 rounded-full shrink-0" 
            style={{ backgroundColor: current.dot }} 
          />
          {current.label}
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="bg-[#0d0d0d]/98 backdrop-blur-xl border-white/[0.09] min-w-[140px] shadow-xl p-1 rounded-xl"
      >
        {STATUS_OPTIONS.map((opt) => (
          <DropdownMenuItem
            key={opt.value}
            onClick={() => mutation.mutate(opt.value)}
            className="text-[12px] text-white/55 focus:text-white hover:text-white focus:bg-white/10 hover:bg-white/10 cursor-pointer gap-2.5 py-2 px-3 rounded-lg transition-colors font-medium outline-none"
          >
            <div
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: opt.dot }}
            />
            {opt.label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
