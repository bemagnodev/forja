import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { RatingHeatmap } from "./RatingHeatmap";
import type { BenchmarkRun } from "./BenchmarkResults";
afterEach(cleanup);

it("distingue erro zero de ausência de comparação e informa a amostra", () => {
  render(<RatingHeatmap runs={[{ id: "a", label: "Modelo A" } as BenchmarkRun]}
    bands={[{ label: "800–1100", total: 3, compared: 1, mae: { a: 0 } },
      { label: "1200–1500", total: 3, compared: 0, mae: { a: null } }]} />);
  const table = screen.getByRole("table", { name: /Erro médio por faixa/ });
  expect(within(table).getByText("0", { exact: true })).toBeInTheDocument();
  expect(within(table).getByText("—")).toBeInTheDocument();
  expect(within(table).getByText("1/3 comparados")).toBeInTheDocument();
  expect(within(table).getByText("0/3 comparados")).toBeInTheDocument();
});
