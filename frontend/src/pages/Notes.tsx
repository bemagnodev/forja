import { PageLayout } from "@/components/layouts/PageLayout";

export function Notes() {
  return (
    <PageLayout
      topbarTitle="Caderno"
      title="Anotações e Snippets"
      description="Sua biblioteca de conhecimento técnico e templates de código."
    >
      <div className="flex items-center justify-center py-32 border border-white/[0.05] rounded-2xl bg-white/[0.008]">
        <span className="text-[13px] text-white/40 font-medium tracking-wide">
          Em breve: organize anotações de estudo e snippets. Esta área ainda está em desenvolvimento.
        </span>
      </div>
    </PageLayout>
  );
}
