
export function getRatingColor(rating: number | null | undefined): string {
  if (rating == null) return "rgba(255, 255, 255, 0.2)";

  if (rating < 1200) return "var(--rating-gray)";
  if (rating < 1400) return "var(--rating-green)";
  if (rating < 1600) return "var(--rating-cyan)";
  if (rating < 1900) return "var(--rating-blue)";
  if (rating < 2100) return "var(--rating-violet)";
  if (rating < 2300) return "var(--rating-orange)";
  if (rating < 2400) return "var(--rating-orange)";
  return "var(--rating-red)";
}
