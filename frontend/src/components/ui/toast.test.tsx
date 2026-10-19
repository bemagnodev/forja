import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ToastProvider } from "./toast";
import { useToast } from "./toast-context";

afterEach(() => { cleanup(); vi.useRealTimers(); });

function Trigger({ duration }: { duration: number }) {
  const { toast } = useToast();
  return <button onClick={() => toast({ title: "Local notification", duration })}>Notify</button>;
}

it("remove automaticamente uma notificação pelo tempo configurado", () => {
  vi.useFakeTimers();
  render(<ToastProvider><Trigger duration={4000} /></ToastProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Notify" }));
  expect(screen.getByText("Local notification")).toBeVisible();
  act(() => vi.advanceTimersByTime(4000));
  expect(screen.queryByText("Local notification")).not.toBeInTheDocument();
});

it("preserva notificações de duração infinita", () => {
  vi.useFakeTimers();
  render(<ToastProvider><Trigger duration={Infinity} /></ToastProvider>);
  fireEvent.click(screen.getByRole("button", { name: "Notify" }));
  act(() => vi.advanceTimersByTime(10000));
  expect(screen.getByText("Local notification")).toBeVisible();
});
