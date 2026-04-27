import { Link, useLocation } from "react-router-dom";
import { useState } from "react";
import {
  Anvil,
  ListChecks,
  TrendingUp,
  SlidersHorizontal,
  Trophy,
  BookMarked,
  UserRound,
  ChevronRight,
} from "lucide-react";

// ─── Rotas de navegação ──────────────────────────────────
// Agrupadas semanticamente: principal e ferramentas
const mainLinks = [
  { name: "Fila",        path: "/",        icon: ListChecks  },
  { name: "Desempenho",  path: "/stats",   icon: TrendingUp  },
  { name: "Conquistas",  path: "/awards",  icon: Trophy      },
  { name: "Caderno",     path: "/notes",   icon: BookMarked  },
];

const toolLinks = [
  { name: "Configurações", path: "/settings", icon: SlidersHorizontal },
];

// ─── Item de Link ─────────────────────────────────────────
function NavItem({
  link,
  isActive,
}: {
  link: { name: string; path: string; icon: React.ElementType };
  isActive: boolean;
}) {
  const Icon = link.icon;
  return (
    <Link
      to={link.path}
      className={[
        "group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150",
        isActive
          ? "text-white bg-[#dc143c]/10 border border-[#dc143c]/20"
          : "text-white/45 hover:text-white/85 hover:bg-white/[0.04] border border-transparent",
      ].join(" ")}
    >
      {/* Acento lateral ativo */}
      {isActive && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-[60%] bg-[#dc143c] rounded-r-full" />
      )}

      <Icon
        className={[
          "w-4 h-4 shrink-0 transition-colors",
          isActive ? "text-[#dc143c]" : "text-white/30 group-hover:text-white/60",
        ].join(" ")}
        strokeWidth={isActive ? 2 : 1.75}
      />

      <span className="flex-1 truncate">{link.name}</span>

      {isActive && (
        <ChevronRight className="w-3 h-3 text-[#dc143c]/50 shrink-0" strokeWidth={2} />
      )}
    </Link>
  );
}

// ─── Sidebar Principal ────────────────────────────────────
export function Sidebar() {
  const location = useLocation();
  const [logoError, setLogoError] = useState(false);

  return (
    <aside className="w-56 shrink-0 min-h-screen flex flex-col border-r border-white/[0.07] bg-[#080808]">

      {/* ── Logo ── */}
      <div className="h-14 flex items-center px-4 border-b border-white/[0.07] gap-2.5 shrink-0">
        <div className="w-8 h-8 rounded-md flex items-center justify-center shrink-0">
          {!logoError ? (
            <img 
              src="/logos/sword.png" 
              alt="Logo Forja" 
              className="w-full h-full object-contain" 
              onError={() => setLogoError(true)} 
            />
          ) : (
            <div className="w-7 h-7 rounded-md bg-[#dc143c]/15 border border-[#dc143c]/25 flex items-center justify-center">
              <Anvil className="w-3.5 h-3.5 text-[#dc143c]" strokeWidth={2} />
            </div>
          )}
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-[14px] font-bold tracking-tight text-white leading-none">Forja</span>
          <span className="text-[9px] text-white/25 tracking-widest uppercase font-medium leading-none">CP Tracker</span>
        </div>
      </div>

      {/* ── Navegação principal ── */}
      <nav className="flex flex-col px-2 py-4 gap-0.5">
        <p className="text-[9px] uppercase tracking-[0.18em] text-white/20 px-3 mb-2 font-bold">
          Principal
        </p>
        {mainLinks.map((link) => (
          <NavItem
            key={link.path}
            link={link}
            isActive={location.pathname === link.path}
          />
        ))}
      </nav>

      {/* Divisor */}
      <div className="mx-4 h-px bg-white/[0.06]" />

      {/* ── Ferramentas ── */}
      <nav className="flex flex-col px-2 py-4 gap-0.5">
        <p className="text-[9px] uppercase tracking-[0.18em] text-white/20 px-3 mb-2 font-bold">
          Sistema
        </p>
        {toolLinks.map((link) => (
          <NavItem
            key={link.path}
            link={link}
            isActive={location.pathname === link.path}
          />
        ))}
      </nav>

      {/* Empurra rodapé para baixo */}
      <div className="flex-1" />

      {/* ── Área do Usuário ── */}
      <div className="border-t border-white/[0.07] p-3 shrink-0">
        <button className="w-full flex items-center gap-2.5 rounded-lg px-2 py-2 hover:bg-white/[0.04] transition-colors group">
          <div className="w-7 h-7 rounded-full bg-[#dc143c]/15 border border-[#dc143c]/20 flex items-center justify-center shrink-0">
            <UserRound className="w-3.5 h-3.5 text-[#dc143c]/80" strokeWidth={1.75} />
          </div>
          <div className="flex flex-col gap-0.5 text-left">
            <span className="text-[12px] font-semibold text-white/70 group-hover:text-white/90 transition-colors leading-none">
              Bernardo
            </span>
            <span className="text-[9px] text-white/25 leading-none">MVP v0.1</span>
          </div>
        </button>
      </div>
    </aside>
  );
}
