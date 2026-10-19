import { createContext, useContext, type ReactNode } from "react";

type ToastType = "success" | "error" | "info" | "warning";
interface ToastAction {
  label: string;
  onClick: () => void;
  icon?: ReactNode;
}
export interface ToastProps {
  title: string;
  description?: string;
  type?: ToastType;
  action?: ToastAction;
  duration?: number;
}
export interface Toast extends ToastProps {
  id: string;
  type: ToastType;
}
export const ToastContext = createContext<{ toast: (props: ToastProps) => void } | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within a ToastProvider");
  return context;
}
