import { Link, useLocation } from "react-router-dom";
import { Hammer, ListTodo, BarChart2, Settings } from "lucide-react";

// Rotas de navegação principal
const links = [
  { name: "Fila", path: "/", icon: ListTodo },
  { name: "Desempenho", path: "/stats", icon: BarChart2 },
  { name: "Configurações", path: "/settings", icon: Settings },
];

export function Sidebar() {
  const location = useLocation();

  return (
    <aside className="w-56 shrink-0 min-h-screen flex flex-col border-r border-white/10 bg-[#0a0a0a]">
      {/* Logo da Forja */}
      <div className="h-14 flex items-center px-5 border-b border-white/10">
        <Hammer className="w-4 h-4 mr-2 text-[#dc143c]" strokeWidth={2.5} />
        <span className="text-[15px] font-bold tracking-wide text-white">
          Forja
        </span>
      </div>

      {/* Seção de navegação */}
      <nav className="flex-1 flex flex-col px-2 py-4 gap-0.5">
        <p className="text-[10px] uppercase tracking-widest text-white/25 px-3 mb-2 font-semibold">
          Navegação
        </p>
        {links.map((link) => {
          const Icon = link.icon;
          const isActive = location.pathname === link.path;
          return (
            <Link
              key={link.path}
              to={link.path}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-[13px] font-medium transition-all duration-150 ${
                isActive
                  ? "bg-[#dc143c]/25 text-white border border-[#dc143c]/50"
                  : "text-white/55 hover:text-white hover:bg-white/5 border border-transparent"
              }`}
            >
              <Icon
                className={`w-3.5 h-3.5 shrink-0 ${isActive ? "text-[#dc143c]" : ""}`}
                strokeWidth={isActive ? 2.5 : 1.8}
              />
              {link.name}
            </Link>
          );
        })}
      </nav>

      {/* Rodapé com versão */}
      <div className="px-5 py-4 border-t border-white/10">
        <p className="text-[10px] text-white/20">Forja · MVP v0.1</p>
      </div>
    </aside>
  );
}

