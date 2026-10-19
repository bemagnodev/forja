import { useState } from "react";
import { BookOpen, Terminal, Code } from "lucide-react";

interface PlatformIconProps {
  platform: string | null;
  type?: string;
}

export function PlatformIcon({ platform, type }: PlatformIconProps) {
  const [imgError, setImgError] = useState(false);
  
  const pKey = (platform || "").trim().toUpperCase();

  // Item de estudo → ícone de livro
  if (type === "STUDY_SESSION") {
    return (
      <div className="flex items-center justify-center shrink-0 w-5 h-5 rounded bg-purple-500/10 border border-purple-500/15">
        <BookOpen className="w-3 h-3 text-purple-400" strokeWidth={2} />
      </div>
    );
  }

  if (!pKey) return <div className="w-5 h-5 shrink-0" />;

  const customLogos: Record<string, string> = {
    CODEFORCES:  "/logos/code-forces.png",
    CODE_FORCES: "/logos/code-forces.png",
    CF:          "/logos/code-forces.png",
    CF_OFFICIAL: "/logos/code-forces.png",
    CF_GYM:      "/logos/code-forces.png",
    ATCODER:     "/logos/atCoder.png",
    AC:          "/logos/atCoder.png",
    CSES:        "/logos/cses.png",
  };

  const fallbacks: Record<string, React.ReactNode> = {
    CODEFORCES:  <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />,
    CODE_FORCES: <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />,
    CF:          <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />,
    CF_OFFICIAL: <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />,
    CF_GYM:      <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />,
    ATCODER:     <Code     className="w-3 h-3 text-sky-400"   strokeWidth={2.5} />,
    AC:          <Code     className="w-3 h-3 text-sky-400"   strokeWidth={2.5} />,
    CSES:        <Code     className="w-3 h-3 text-amber-500" strokeWidth={2.5} />,
  };

  // Mapeamento dinâmico para logos
  let src = customLogos[pKey];
  let fallback = fallbacks[pKey];

  // Lógica de detecção inteligente para Codeforces (pode vir como CF, CF_OFFICIAL, etc)
  if (!src && (pKey.includes("CODE") || pKey.includes("CF"))) {
    src = "/logos/code-forces.png";
    fallback = <Terminal className="w-3 h-3 text-[#dc143c]" strokeWidth={2.5} />;
  }
  
  // Lógica de detecção inteligente para AtCoder
  if (!src && (pKey.includes("ATCODER") || pKey === "AC")) {
    src = "/logos/atCoder.png";
    fallback = <Code className="w-3 h-3 text-sky-400" strokeWidth={2.5} />;
  }

  // Lógica de detecção inteligente para CSES
  if (!src && pKey.includes("CSES")) {
    src = "/logos/cses.png";
    fallback = <Code className="w-3 h-3 text-amber-500" strokeWidth={2.5} />;
  }


  // AtCoder: Preencher o quadrado todo se possível
  if ((pKey === "ATCODER" || pKey === "AC" || (src === "/logos/atCoder.png")) && !imgError) {
    return (
      <div className="flex items-center justify-center shrink-0 w-5 h-5 rounded overflow-hidden bg-white border border-white">
        <img
          src="/logos/atCoder.png"
          alt={platform || ""}
          className="w-full h-full object-cover"
          onError={() => setImgError(true)}
        />
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center shrink-0 w-5 h-5 rounded bg-white/[0.05] border border-white/[0.08] overflow-hidden">
      {!src || imgError
        ? (fallback ?? <span className="text-[9px] text-[#dc143c] font-bold">{pKey[0]}</span>)
        : (
          <img
            src={src}
            alt={platform || ""}
            className="w-[85%] h-[85%] object-contain"
            onError={() => setImgError(true)}
          />
        )
      }
    </div>
  );
}
