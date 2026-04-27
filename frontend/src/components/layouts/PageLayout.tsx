import React from "react";

interface PageLayoutProps {
  topbarTitle?: string;
  title: string;
  badge?: React.ReactNode;
  description?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}

export function PageLayout({
  topbarTitle,
  title,
  badge,
  description,
  action,
  children,
}: PageLayoutProps) {
  return (
    <div className="flex flex-col min-h-full bg-transparent relative overflow-x-hidden">
      {/* Blobs decorativos — opacidade reduzida para não poluir, e usa cor primary do design system */}
      <div className="absolute top-[-8%] left-[-8%] w-[35%] h-[35%] bg-primary/[0.035] blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-8%] right-[-4%] w-[28%] h-[42%] bg-purple-900/[0.03] blur-[120px] rounded-full pointer-events-none" />

      {/* ── Topbar da página ── */}
      {topbarTitle && (
        <header className="h-14 border-b border-white/[0.06] flex items-center px-8 relative z-10 bg-black/15 backdrop-blur-md">
          <span className="text-[10px] font-bold text-white/20 tracking-[0.22em] uppercase">
            {topbarTitle}
          </span>
        </header>
      )}

      {/* ── Conteúdo ── */}
      <div className="flex-1 p-8 md:p-10 max-w-[1400px] w-full mx-auto relative z-10">
        {/* Título + Ação */}
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
              {title}
              {badge}
            </h2>
            {description && (
              <p className="text-[13px] text-white/30 mt-1 font-medium">
                {description}
              </p>
            )}
          </div>
          {action && <div>{action}</div>}
        </div>

        {/* Children (eg. Tabela, Gráficos) */}
        {children}
      </div>
    </div>
  );
}
