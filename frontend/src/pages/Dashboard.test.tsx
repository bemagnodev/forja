import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";
import { fetchDashboardStats } from "@/lib/api-dashboard";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

function renderDashboard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><Dashboard /></QueryClientProvider>);
}

vi.mock("@/lib/api-dashboard", () => ({ fetchDashboardStats: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("shows Atualizar in the page header and retries loading when clicked", async () => {
  vi.mocked(fetchDashboardStats).mockRejectedValue(new Error("Falha simulada"));
  const user = userEvent.setup();
  renderDashboard();
  expect(await screen.findByText("Falha simulada")).toBeVisible();
  expect(fetchDashboardStats).toHaveBeenCalledTimes(1);
  const refresh = screen.getByRole("button", { name: "Atualizar" });
  expect(refresh).toBeVisible();
  await user.click(refresh);
  await waitFor(() => expect(fetchDashboardStats).toHaveBeenCalledTimes(2));
});

it('refreshes dashboard when Codeforces synchronization really completes', async () => {
  vi.mocked(fetchDashboardStats).mockRejectedValue(new Error('Falha simulada'));
  renderDashboard();
  await screen.findByText('Falha simulada');
  act(() => { window.dispatchEvent(new Event('forja:cf-sync-completed')); });
  await waitFor(() => expect(fetchDashboardStats).toHaveBeenCalledTimes(2));
});
