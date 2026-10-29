import React from "react";

interface PageLayoutProps {
  topbarTitle?: string;
  title: React.ReactNode;
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
      {/* ── Topbar da página ── */}
      {topbarTitle && (
        <header className="h-10 shrink-0 border-b border-white/[0.06] flex items-center px-5 md:px-8 relative z-10">
          <span className="text-[11px] font-medium text-zinc-400">
            {topbarTitle}
          </span>
        </header>
      )}

      {/* ── Conteúdo ── */}
      <div className="flex-1 p-5 md:px-8 md:py-6 max-w-[1400px] w-full mx-auto relative z-10">
        {/* Título + Ação */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
          <div className="min-w-0 flex-1 basis-64">
            <h2 className="text-2xl font-bold text-white tracking-tight flex flex-wrap items-center gap-3">
              {title}
              {badge}
            </h2>
            {description && (
              <p className="text-[13px] text-zinc-400 mt-1">
                {description}
              </p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>

        {/* Children (eg. Tabela, Gráficos) */}
        {children}
      </div>
    </div>
  );
}
