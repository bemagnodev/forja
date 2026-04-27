export interface QueueItem {
  id: number;
  item_type: "PROBLEM" | "STUDY_SESSION";
  title: string;
  description: string | null;
  source_platform: string | null;
  priority: "P0" | "P1" | "P2" | "UPSOLVING";
  is_completed: boolean;
  tags: string[];
  order: number;
  created_at: string;
  resolved_at: string | null;
  rating?: number;
  url?: string;
  already_solved?: boolean;
}

export interface ProblemResult {
  id: number;
  platform_id: string;
  title: string;
  platform: string;
}
