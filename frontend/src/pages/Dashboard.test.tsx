import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { Dashboard } from "./Dashboard";
import { fetchDashboardStats } from "@/lib/api-dashboard";

vi.mock("@/lib/api-dashboard", () => ({ fetchDashboardStats: vi.fn() }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("shows Refresh in the page header and retries loading when clicked", async () => {
  vi.mocked(fetchDashboardStats).mockRejectedValue(new Error("Falha simulada"));
  const user = userEvent.setup();
  render(<Dashboard />);
  expect(await screen.findByText("Falha simulada")).toBeVisible();
  expect(fetchDashboardStats).toHaveBeenCalledTimes(1);
  const refresh = screen.getByRole("button", { name: "Refresh" });
  expect(refresh).toBeVisible();
  await user.click(refresh);
  await waitFor(() => expect(fetchDashboardStats).toHaveBeenCalledTimes(2));
});
