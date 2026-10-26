from datetime import timedelta, datetime, time
from django.utils import timezone
from django.db.models import Count, Q, Avg
from collections import defaultdict
from api.models import Submission, UserProblemTracking, ContestParticipation, Problem

def get_dashboard_stats(user):
    now = timezone.now()
    thirty_days_ago = now - timedelta(days=30)
    today = timezone.localdate(now)
    one_year_ago = timezone.make_aware(datetime.combine(today - timedelta(days=364), time.min))
    seven_days_ago = timezone.make_aware(datetime.combine(today - timedelta(days=6), time.min))
    tomorrow = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))

    # 1. Base Queries
    acs_qs = Submission.objects.filter(
        user=user, 
        verdict__in=['OK', 'AC']
    )
    
    # Trackings com status 'DONE' ou resolvidos
    solved_trackings = UserProblemTracking.objects.filter(
        user=user, 
        review_status='DONE'
    ).select_related('problem')

    total_solved = solved_trackings.count()
    
    total_submissions = Submission.objects.filter(user=user).count()
    total_acs_submissions = acs_qs.count()
    acceptance_rate = round((total_acs_submissions / total_submissions * 100) if total_submissions > 0 else 0, 1)

    solved_this_month = acs_qs.filter(creation_time__gte=thirty_days_ago).values('problem').distinct().count()

    # 2. Heatmap & Streaks
    # Extrair dias com AC no último ano
    acs_last_year = acs_qs.filter(creation_time__gte=one_year_ago, creation_time__lt=tomorrow).order_by('creation_time')
    
    daily_counts = defaultdict(int)
    for sub in acs_last_year:
        # Pega a data local (ou UTC se preferir, simplificaremos pegando a string iso da data)
        day_str = timezone.localdate(sub.creation_time).isoformat()
        daily_counts[day_str] += 1

    heatmap = [{"date": k, "count": v} for k, v in daily_counts.items()]
    
    # Calcular Streaks
    sorted_days = sorted(daily_counts.keys(), reverse=True)
    current_streak = 0
    max_streak = 0
    temp_streak = 0
    
    # Usaremos iteracão de datas para calcular a streak corretamente
    date_iter = today
    # Verifica se hoje tem AC, se não, começa de ontem (streak atual pode não ter sido feita hoje ainda)
    if date_iter.isoformat() not in daily_counts:
        date_iter -= timedelta(days=1)
        
    while date_iter.isoformat() in daily_counts:
        current_streak += 1
        date_iter -= timedelta(days=1)
        
    # Calcular Max Streak percorrendo todo o mapa (abordagem simplificada iterando os dias ativos)
    all_active_dates = sorted([timezone.datetime.fromisoformat(d).date() for d in daily_counts.keys()])
    if all_active_dates:
        temp_streak = 1
        max_streak = 1
        for i in range(1, len(all_active_dates)):
            if (all_active_dates[i] - all_active_dates[i-1]).days == 1:
                temp_streak += 1
                max_streak = max(max_streak, temp_streak)
            else:
                temp_streak = 1

    kpis = {
        "total_solved": total_solved,
        "streak": current_streak,
        "max_streak": max_streak,
        "acceptance_rate": acceptance_rate,
        "solved_this_month": solved_this_month
    }

    # 3. Last 7 Days Widget
    last_7_days_activity = []
    last_7_days_solved_count = 0
    recent_problems = set()
    ratings = []
    topics_7d = defaultdict(int)
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        has_activity = daily_counts.get(day_str, 0) > 0
        last_7_days_activity.append(has_activity)
        
    # Extrair dados das questões da última semana
    recent_acs = acs_qs.filter(creation_time__gte=seven_days_ago, creation_time__lt=tomorrow).select_related('problem')
    
    for sub in recent_acs:
        if sub.problem.id not in recent_problems:
            recent_problems.add(sub.problem.id)
            last_7_days_solved_count += 1
            meta = sub.problem.platform_metadata or {}
            if meta.get('rating'):
                ratings.append(meta.get('rating'))
            for tag in meta.get('tags', []):
                topics_7d[tag] += 1
                
    avg_diff = int(sum(ratings) / len(ratings)) if ratings else 0
    top_topics_7d = [{"name": k, "count": v} for k, v in sorted(topics_7d.items(), key=lambda item: item[1], reverse=True)[:3]]

    last_7_days = {
        "activity": last_7_days_activity,
        "dates": [(today - timedelta(days=i)).isoformat() for i in range(6, -1, -1)],
        "total_solved": last_7_days_solved_count,
        "average_difficulty": avg_diff,
        "top_topics": top_topics_7d
    }

    # 4. Difficulty Breakdown & Topics (Todos os problemas resolvidos)
    difficulty_breakdown = defaultdict(int)
    topics_breakdown = defaultdict(lambda: {"solved": 0})
    
    for t in solved_trackings:
        meta = t.problem.platform_metadata or {}
        
        # Agrupar difficulty em "buckets" de 100
        rating = meta.get('rating')
        if rating:
            bucket = (rating // 100) * 100
            difficulty_breakdown[str(bucket)] += 1
            
        # Agrupar tags
        for tag in meta.get('tags', []):
            topics_breakdown[tag]["solved"] += 1
            
    # A taxa por tópico ainda não é calculada; não publicar um percentual fictício.
    topics = []
    for tag, data in sorted(topics_breakdown.items(), key=lambda x: x[1]['solved'], reverse=True)[:15]:
        topics.append({
            "name": tag,
            "solved": data["solved"],
            "accuracy": None
        })

    # 5. Recent Contests
    # Reutiliza lógica da view, mas limita a 5
    participations = list(ContestParticipation.objects.select_related('contest').filter(user=user).order_by('-participation_date')[:5])
    contest_ids = [p.contest_id for p in participations]

    trackings = UserProblemTracking.objects.filter(
        user=user, problem__contest_id__in=contest_ids
    ).values('problem__contest_id', 'system_status')

    counts_by_contest = {cid: {'solved_live': 0, 'pending_upsolve': 0, 'upsolved': 0, 'unattempted': 0, 'total': 0} for cid in contest_ids}
    for tr in trackings:
        cid = tr['problem__contest_id']
        st = tr['system_status']
        counts_by_contest[cid]['total'] += 1
        if st == 'SOLVED_LIVE': counts_by_contest[cid]['solved_live'] += 1
        elif st == 'PENDING_UPSOLVE': counts_by_contest[cid]['pending_upsolve'] += 1
        elif st == 'UPSOLVED': counts_by_contest[cid]['upsolved'] += 1
        elif st == 'UNATTEMPTED': counts_by_contest[cid]['unattempted'] += 1

    recent_contests = []
    for p in participations:
        prog = counts_by_contest.get(p.contest_id, {'solved_live': 0, 'pending_upsolve': 0, 'upsolved': 0, 'unattempted': 0, 'total': 0})
        recent_contests.append({
            "id": p.id,
            "contest_id": p.contest.id,
            "name": p.contest.name,
            "platform": p.contest.platform,
            "date": p.participation_date.isoformat() if p.participation_date else None,
            "progress": prog
        })

    # 6. Recent ACs
    recent_acs_qs = acs_qs.select_related('problem').order_by('-creation_time')[:10]
    recent_acs = []
    for sub in recent_acs_qs:
        meta = sub.problem.platform_metadata or {}
        recent_acs.append({
            "id": sub.id,
            "problem_name": sub.problem.title,
            "platform": sub.problem.platform,
            "tags": meta.get('tags', [])[:3],
            "date": sub.creation_time.isoformat(),
            "url": sub.problem.url
        })

    return {
        "reference_date": today.isoformat(),
        "timezone": timezone.get_current_timezone_name(),
        "kpis": kpis,
        "heatmap": heatmap,
        "last_7_days": last_7_days,
        "difficulty_breakdown": difficulty_breakdown,
        "topics": topics,
        "recent_contests": recent_contests,
        "recent_acs": recent_acs
    }
