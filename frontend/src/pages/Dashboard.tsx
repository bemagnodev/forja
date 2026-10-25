import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageLayout } from "@/components/layouts/PageLayout";
import { fetchDashboardStats } from "@/lib/api-dashboard";
import { KPICards } from "@/components/dashboard/KPICards";
import { ActivityHeatmap } from "@/components/dashboard/ActivityHeatmap";
import { Last7DaysWidget } from "@/components/dashboard/Last7DaysWidget";
import { DifficultyBreakdown } from "@/components/dashboard/DifficultyBreakdown";
import { TopicMastery } from "@/components/dashboard/TopicMastery";
import { RecentContestsList } from "@/components/dashboard/RecentContestsList";
import { RecentACsList } from "@/components/dashboard/RecentACsList";
import { RefreshCw } from "lucide-react";

export function Dashboard() {
  const { data: stats, isPending, isFetching, error: queryError, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboardStats,
    retry: false,
  });
  const loading = isPending || isFetching;
  const error = queryError?.message;

  useEffect(() => {
    const onSyncCompleted = () => { void refetch(); };
    window.addEventListener('forja:cf-sync-completed', onSyncCompleted);
    return () => window.removeEventListener('forja:cf-sync-completed', onSyncCompleted);
  }, [refetch]);

  return (
    <PageLayout
      topbarTitle="Dashboard"
      title="A Forja"
      description="Sua visão geral de progressão."
      action={
        <button 
          onClick={() => { void refetch(); }}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800/50 hover:bg-zinc-800 rounded-md transition-colors border border-zinc-700/50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      }
    >
      {loading && !stats ? (
        <div className="flex items-center justify-center py-32">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-red-500 border-r-2 border-r-transparent"></div>
        </div>
      ) : error ? (
        <div className="flex items-center justify-center py-32 border border-red-900/30 rounded-2xl bg-red-950/20 text-red-400">
          <p>{error}</p>
        </div>
      ) : stats ? (
        <div className="flex flex-col gap-6 pb-12">
          <KPICards kpis={stats.kpis} />
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <ActivityHeatmap data={stats.heatmap} />
            </div>
            <div className="lg:col-span-1">
              <Last7DaysWidget data={stats.last_7_days} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-1">
              <DifficultyBreakdown data={stats.difficulty_breakdown} />
            </div>
            <div className="lg:col-span-2">
              <TopicMastery data={stats.topics} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <RecentContestsList data={stats.recent_contests} />
            <RecentACsList data={stats.recent_acs} />
          </div>
        </div>
      ) : null}
    </PageLayout>
  );
}
