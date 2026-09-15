import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { EmberBackground } from "./EmberBackground";

describe("EmberBackground", () => {
  it("renderiza como elemento decorativo inacessível (aria-hidden e pointer-events-none)", () => {
    const { container } = render(<EmberBackground />);
    const root = container.firstElementChild as HTMLElement;

    expect(root).toBeInTheDocument();
    expect(root).toHaveAttribute("aria-hidden", "true");
    expect(root.className).toContain("pointer-events-none");
  });

  it("renderiza a quantidade esperada de aproximadamente 30-36 brasas", () => {
    const { container } = render(<EmberBackground />);
    const embers = container.querySelectorAll("[data-testid='ember-particle']");

    expect(embers.length).toBe(32);
  });

  it("garante estabilidade dos estilos das brasas após rerender", () => {
    const { container, rerender } = render(<EmberBackground />);
    const initialEmbers = Array.from(container.querySelectorAll("[data-testid='ember-particle']")).map(
      (el) => (el as HTMLElement).style.cssText
    );

    rerender(<EmberBackground />);

    const rerenderedEmbers = Array.from(container.querySelectorAll("[data-testid='ember-particle']")).map(
      (el) => (el as HTMLElement).style.cssText
    );

    expect(rerenderedEmbers).toEqual(initialEmbers);
  });

  it("distribui partículas nas regiões esquerda, central e direita", () => {
    const { container } = render(<EmberBackground />);
    const embers = Array.from(container.querySelectorAll("[data-testid='ember-particle']")) as HTMLElement[];

    const leftPositions = embers.map((el) => parseFloat(el.style.left));

    const leftZone = leftPositions.filter((pos) => pos < 33);
    const centerZone = leftPositions.filter((pos) => pos >= 33 && pos <= 67);
    const rightZone = leftPositions.filter((pos) => pos > 67);

    expect(leftZone.length).toBeGreaterThan(0);
    expect(centerZone.length).toBeGreaterThan(0);
    expect(rightZone.length).toBeGreaterThan(0);
  });
});
