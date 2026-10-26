import { PageLayout } from "@/components/layouts/PageLayout";

export function Profile() {
  return (
    <PageLayout
      topbarTitle="Usuário"
      title="Seu Perfil"
      description="Estatísticas pessoais e informações da conta."
    >
      <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
        <span className="text-[13px] text-white/40 font-medium tracking-wide">
          Em breve: informações e estatísticas pessoais. Esta área ainda está em desenvolvimento.
        </span>
      </div>
    </PageLayout>
  );
}
