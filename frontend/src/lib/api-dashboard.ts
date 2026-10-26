import { api } from "./api";

export interface DashboardKPIs {
  total_solved: number;
  streak: number;
  max_streak: number;
  acceptance_rate: number;
  solved_this_month: number;
}

export interface HeatmapData {
  date: string;
  count: number;
}

export interface Last7DaysStats {
  activity: boolean[];
  total_solved: number;
  average_difficulty: number;
  top_topics: { name: string; count: number }[];
}

export interface TopicStat {
  name: string;
  solved: number;
  accuracy: number | null;
}

export interface RecentContest {
  id: number;
  contest_id: number;
  name: string;
  platform: string;
  date: string | null;
  progress: {
    solved_live: number;
    pending_upsolve: number;
    upsolved: number;
    unattempted: number;
    total: number;
  };
}

export interface RecentAC {
  id: number;
  problem_name: string;
  platform: string;
  tags: string[];
  date: string;
  url?: string;
}

export interface DashboardStats {
  kpis: DashboardKPIs;
  heatmap: HeatmapData[];
  last_7_days: Last7DaysStats;
  difficulty_breakdown: Record<string, number>;
  topics: TopicStat[];
  recent_contests: RecentContest[];
  recent_acs: RecentAC[];
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await api.get('/dashboard/stats');
  return response.data;
}
