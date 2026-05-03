import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { CheckCircle2, X, Info, AlertCircle, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info" | "warning";

interface ToastAction {
  label: string;
  onClick: () => void;
  icon?: React.ReactNode;
}

interface Toast {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
  action?: ToastAction;
  duration?: number;
}

interface ToastProps {
  title: string;
  description?: string;
  type?: ToastType;
  action?: ToastAction;
  duration?: number;
}

interface ToastContextType {
  toast: (props: ToastProps) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback(({ title, description, type = "success", action, duration = 4000 }: ToastProps) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, title, description, type, action, duration }]);
    
    // Auto remove
    if (duration !== Infinity) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[100] flex flex-col items-center gap-3 pointer-events-none w-full max-w-md px-6">
        {toasts.map((t) => (
          <ToastItem key={t.id} toast={t} onDismiss={() => removeToast(t.id)} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const [isExiting, setIsExiting] = useState(false);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(onDismiss, 300);
  };

  const handleAction = () => {
    if (toast.action) {
      toast.action.onClick();
      handleDismiss();
    }
  };

  const icons = {
    success: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
    error: <AlertCircle className="w-5 h-5 text-red-400" />,
    info: <Info className="w-5 h-5 text-blue-400" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400" />,
  };

  const borders = {
    success: "border-emerald-500/20 shadow-emerald-500/5",
    error: "border-red-500/20 shadow-red-500/5",
    info: "border-blue-500/20 shadow-blue-500/5",
    warning: "border-amber-500/20 shadow-amber-500/5",
  };

  const accentColors = {
    success: "text-emerald-400",
    error: "text-red-400",
    info: "text-blue-400",
    warning: "text-amber-400",
  };

  return (
    <div
      className={cn(
        "pointer-events-auto flex items-center gap-4 bg-zinc-950/90 backdrop-blur-xl border p-4 rounded-xl shadow-2xl transition-all duration-300 w-full md:min-w-[400px]",
        borders[toast.type]
      )}
      style={{
        animation: isExiting 
          ? "toastOut 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards" 
          : "toastIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) both"
      }}
    >
      <div className="shrink-0">
        {icons[toast.type]}
      </div>
      
      <div className="flex-1 flex flex-col gap-0.5 overflow-hidden">
        <h3 className={cn("text-[13px] font-bold tracking-tight leading-none truncate", accentColors[toast.type])}>
          {toast.title}
        </h3>
        {toast.description && (
          <p className="text-[11px] text-white/50 leading-relaxed truncate">
            {toast.description}
          </p>
        )}
      </div>

      {toast.action && (
        <div className="flex items-center gap-3 shrink-0 ml-2">
          <div className="w-px h-6 bg-white/10" />
          <button
            onClick={handleAction}
            className="flex items-center gap-1.5 text-[11px] font-bold text-white hover:text-emerald-400 uppercase tracking-wider transition-colors px-2 py-1 rounded-md hover:bg-white/5 active:scale-95"
          >
            {toast.action.icon}
            {toast.action.label}
          </button>
        </div>
      )}

      <button
        onClick={handleDismiss}
        className="shrink-0 p-1 rounded-lg text-white/20 hover:text-white hover:bg-white/5 transition-all ml-1"
      >
        <X className="w-4 h-4" />
      </button>

      <style>{`
        @keyframes toastIn {
          0% { opacity: 0; transform: translateY(20px) scale(0.95); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        @keyframes toastOut {
          0% { opacity: 1; transform: translateY(0) scale(1); }
          100% { opacity: 0; transform: translateY(15px) scale(0.98); }
        }
      `}</style>
    </div>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}
