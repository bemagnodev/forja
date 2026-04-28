import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLayout } from "@/components/layouts/PageLayout";
import { ContestCard, type ContestParticipation } from "@/components/contests/ContestCard";
import { ContestMetrics } from "@/components/contests/ContestMetrics";
import { AlertCircle, Swords } from "lucide-react";

export function Contests() {
  const { data: participations = [], isLoading, isError } = useQuery<ContestParticipation[]>({
    queryKey: ["contests"],
    queryFn: async () => {
      const { data } = await api.get("/contests");
      return data;
    },
  });

  return (
    <PageLayout
      topbarTitle="Upsolving"
      title="Meus Contests"
      description="Acompanhe sua dívida técnica e identifique o que ainda precisa ser resolvido."
    >
      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-32">
          <div className="flex flex-col items-center gap-4">
            <div className="w-6 h-6 rounded-full border-2 border-primary border-t-transparent animate-spin" />
            <span className="text-[11px] text-white/25 font-medium tracking-widest uppercase">
              Carregando contests...
            </span>
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
            <p className="text-[12px] opacity-60 mt-0.5">
              Não foi possível conectar com o servidor. Django está rodando?
            </p>
          </div>
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* Header de métricas globais */}
          <ContestMetrics participations={participations} />

          {/* Estado vazio */}
          {participations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-32 rounded-2xl border border-white/[0.05] bg-white/[0.008]">
              <div className="w-14 h-14 rounded-full bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-4">
                <Swords className="w-6 h-6 text-white/20" strokeWidth={1.5} />
              </div>
              <p className="text-[14px] font-bold text-white/70">Nenhum contest sincronizado.</p>
              <p className="text-[12px] text-white/40 mt-1">
                Use o botão "Sincronizar CF" na sidebar para importar seus contests.
              </p>
            </div>
          ) : (
            /* Grid de cards */
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {participations.map((p) => (
                <ContestCard key={p.id} participation={p} />
              ))}
            </div>
          )}
        </>
      )}
    </PageLayout>
  );
}
