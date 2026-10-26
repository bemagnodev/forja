// Tipos compartilhados para a feature de Contests/Upsolving
export interface ContestResult {
  accepted: boolean | null;
  failed_attempts: number | null;
  first_ac_seconds: number | null;
  errors_before_ac: Record<string, number>;
  errors_after_ac: Record<string, number>;
  compilation_errors: number;
  coverage: 'complete' | 'partial';
  is_upsolved: boolean;
  upsolved_at: string | null;
  manual_completion: boolean;
}

export interface ContestProblem {
  id: number;
  platform_id: string;
  title: string;
  index: string;
  rating: number | null;
  ai_rating: number | null;
  tags: string[];
  ai_tags: string[];
  ai_visual_status?: string | null;
  url: string | null;
  system_status: string;
  review_status: string;
  tracking_id: number | null;
  contest_result?: ContestResult | null;
}
