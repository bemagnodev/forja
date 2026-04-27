import { RefreshCw, X } from "lucide-react";
import { useEffect, useState } from "react";

export function UndoToast({
  title,
  onUndo,
  onDismiss,
}: {
  title: string;
  onUndo: () => void;
  onDismiss: () => void;
}) {
  const [isExiting, setIsExiting] = useState(false);

  const startExit = () => {
    setIsExiting(true);
    setTimeout(onDismiss, 300);
  };

  const handleUndo = () => {
    setIsExiting(true);
    setTimeout(onUndo, 300);
  };

  useEffect(() => {
    const timer = setTimeout(startExit, 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div
      className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 pointer-events-none"
      style={{
        animation: isExiting 
          ? "toastOut 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards" 
          : "toastIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both"
      }}
    >
      <div className="flex items-center gap-4 bg-zinc-950/90 pointer-events-auto backdrop-blur-xl border border-[#dc143c]/15 text-white px-5 py-3 rounded-xl shadow-[0_8px_30px_rgba(0,0,0,0.5)] transition-all hover:bg-[#111] hover:border-[#dc143c]/40 hover:shadow-[0_8px_30px_rgba(220,20,60,0.1)]">
        
        <div className="flex flex-col gap-0.5">
          <span className="text-[13px] font-semibold text-[#dc143c] max-w-[200px] truncate leading-tight">
            Item finalizado
          </span>
          <span className="text-[11px] text-white/50 truncate max-w-[200px]">
            {title}
          </span>
        </div>

        <div className="w-px h-6 bg-white/10 shrink-0" />

        <button
          onClick={handleUndo}
          className="flex items-center gap-1.5 text-[12px] font-bold text-white hover:text-[#dc143c] uppercase tracking-wider transition-colors shrink-0 px-2 py-1 rounded-md hover:bg-[#dc143c]/10 active:scale-95"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Desfazer
        </button>

        <button
          onClick={startExit}
          className="text-white/30 hover:text-white transition-colors shrink-0 p-1.5 rounded-full hover:bg-white/10 active:scale-95 ml-1"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <style>{`
        @keyframes toastIn {
          0% { opacity: 0; transform: translate(-50%, 20px) scale(0.9); }
          100% { opacity: 1; transform: translate(-50%, 0) scale(1); }
        }
        @keyframes toastOut {
          0% { opacity: 1; transform: translate(-50%, 0) scale(1); }
          100% { opacity: 0; transform: translate(-50%, 15px) scale(0.95); }
        }
      `}</style>
    </div>
  );
}
