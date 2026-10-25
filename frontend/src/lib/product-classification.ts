export const NATIVE_RATING_MESSAGE =
  'Não é possível classificar com IA: esta questão já possui rating nativo da plataforma.';

export function hasNativeRating(rating: unknown): rating is number {
  return typeof rating === 'number' && Number.isFinite(rating);
}
