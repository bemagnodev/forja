import { PageLayout } from "@/components/layouts/PageLayout";

export function Dashboard() {
  return (
    <PageLayout
      topbarTitle="Dashboard"
      title="Visão Geral"
      description="Resumo do seu progresso e estatísticas recentes."
    >
      <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
        <span className="text-[13px] text-white/40 font-medium tracking-wide">
          Dashboard em construção...
        </span>
      </div>
    </PageLayout>
  );
}
