import { PageLayout } from "@/components/layouts/PageLayout";

export function Teams() {
  return (
    <PageLayout
      topbarTitle="Equipes"
      title="Minhas Equipes"
      description="Gerencie seus times para competições e treinos conjuntos."
    >
      <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
        <span className="text-[13px] text-white/40 font-medium tracking-wide">
          Módulo de equipes em construção...
        </span>
      </div>
    </PageLayout>
  );
}
