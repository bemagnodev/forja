export interface QueueItem {
  id: number;
  item_type: "PROBLEM" | "STUDY_SESSION";
  title: string;
  description: string | null;
  source_platform: string | null;
  linked_problem_id?: number | null;
  priority: "P0" | "P1" | "P2" | "UPSOLVING" | "FUTURE";
  is_completed: boolean;
  tags: string[];
  order: number;
  created_at: string;
  resolved_at: string | null;
  rating?: number;
  url?: string;
  already_solved?: boolean;
  platform_id?: string | null;
  // Título real do problema vinculado (pode diferir do título livre do QueueItem)
  problem_title?: string | null;
  // Nome do contest ao qual o problema pertence
  contest_name?: string | null;
  ai_rating?: number | null;
  ai_tags?: string[];
  ai_visual_status?: string | null;
}


export interface ProblemResult {
  id: number;
  platform_id: string;
  title: string;
  platform: string;
}

export interface QueueCreateInput {
  title: string;
  description: string | null;
  item_type: string;
  priority: string;
  source_platform: string | null;
  linked_problem_id: number | null;
}
