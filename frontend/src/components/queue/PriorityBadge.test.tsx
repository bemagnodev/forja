import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { PriorityBadge } from "./PriorityBadge";

describe("PriorityBadge", () => {
  it("renders P0 correctly", () => {
    render(<PriorityBadge priority="P0" />);
    expect(screen.getByText("P0")).toBeInTheDocument();
  });

  it("renders FUTURE correctly", () => {
    render(<PriorityBadge priority="FUTURE" />);
    expect(screen.getByText("Futuro")).toBeInTheDocument();
  });

  it("returns null for unknown priority", () => {
    const { container } = render(<PriorityBadge priority="UNKNOWN" />);
    expect(container).toBeEmptyDOMElement();
  });
});
