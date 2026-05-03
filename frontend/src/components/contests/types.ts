// Tipos compartilhados para a feature de Contests/Upsolving
export interface ContestProblem {
  id: number;
  platform_id: string;
  title: string;
  index: string;
  rating: number | null;
  ai_rating: number | null;
  tags: string[];
  ai_tags: string[];
  url: string | null;
  system_status: string;
  review_status: string;
  tracking_id: number | null;
}
