import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { PredictionChart } from "./PredictionChart";
import type { BenchmarkRun } from "./BenchmarkResults";
afterEach(cleanup);

it('counts problems rather than overlapping circles and excludes invalid ratings', () => {
  render(<PredictionChart run={{ id: 'a', label: 'A' } as BenchmarkRun} onSelect={vi.fn()}
    problems={[1000, 800, 1200, 1200, null].map((rating, i) => ({ key: String(i),
      reference: { rating: 1000, tags: [] }, predictions: { a: {
        rating, rating_status: rating == null ? 'invalid_output' : 'valid', tags_status: 'valid' } } }))} />);
  const distribution = screen.getByRole('group', { name: 'Distribuição das estimativas' });
  expect(distribution).toHaveTextContent('4/5 previsões válidas');
  expect(distribution).toHaveTextContent('Rating exato: 1 (25%)');
  expect(distribution).toHaveTextContent('Subestimadas: 1 (25%)');
  expect(distribution).toHaveTextContent('Superestimadas: 2 (50%)');
});

it("agrupa coordenadas coincidentes sem deslocar os ratings nem exibir códigos", async () => {
  const onSelect = vi.fn();
  const user = userEvent.setup();
  render(<PredictionChart run={{ id: "a", label: "Modelo A" } as BenchmarkRun} onSelect={onSelect}
    problems={["101A", "102B"].map(key => ({ key, reference: { rating: 1000, tags: [] },
      predictions: { a: { rating: 1200, rating_status: "valid", tags_status: "valid" } } }))} />);
  const point = screen.getByRole("button", { name: /Oficial 1000, estimado 1200.*2 problemas/ });
  expect(screen.getAllByRole("button")).toHaveLength(1);
  expect(screen.queryByText("101A")).not.toBeInTheDocument();
  await user.click(point);
  expect(onSelect).toHaveBeenCalledWith(["101A", "102B"]);
  expect(screen.getByRole("tooltip")).toHaveTextContent("Superestimou em 200 pontos");
});
