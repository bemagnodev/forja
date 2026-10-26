import { PageLayout } from "@/components/layouts/PageLayout";

export function Settings() {
  return (
    <PageLayout
      topbarTitle="Sistema"
      title="Configurações"
      description="Ajuste suas preferências, conexões de API e opções da conta."
    >
      <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
        <span className="text-[13px] text-white/40 font-medium tracking-wide">
          Em breve: preferências e opções da conta. Os controles desta área ainda não estão disponíveis.
        </span>
      </div>
    </PageLayout>
  );
}
