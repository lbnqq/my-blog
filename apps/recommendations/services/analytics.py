from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import (
    Avg,
    Case,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    FloatField,
    Q,
    Value,
    When,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie, UpcomingMovieNews
from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.ratings.models import RatingForm, UserRating, UserSession
from apps.recommendations.models import RecommendationFeedback, RecommendationResult, SyncRun


PERIODS = {"today", "7d", "30d", "all", "custom"}
YEAR_RANGES = {"all", "2020", "2010", "2000", "1990", "pre1990"}
MOVIE_SORTS = {"recommendations", "average_rating", "coverage"}


def percentage(part, total):
    return part / total * 100 if total else 0.0


@dataclass(frozen=True)
class AnalyticsFilters:
    period: str = "7d"
    category: str = ""
    version: str = ""
    user_type: str = "all"
    year_range: str = "all"
    sort: str = "recommendations"
    date_from: object = None
    date_to: object = None

    @classmethod
    def from_request(cls, request):
        period = request.GET.get("period", "7d")
        if period not in PERIODS:
            period = "7d"
        category = request.GET.get("category", "")
        if category not in CATEGORY_LABELS:
            category = ""
        version = request.GET.get("version", "").strip()[:32]
        user_type = request.GET.get("user_type", "all")
        if user_type not in {"all", "authenticated", "guest"}:
            user_type = "all"
        year_range = request.GET.get("year", "all")
        if year_range not in YEAR_RANGES:
            year_range = "all"
        sort = request.GET.get("sort", "recommendations")
        if sort not in MOVIE_SORTS:
            sort = "recommendations"
        date_from = _parse_date(request.GET.get("date_from"))
        date_to = _parse_date(request.GET.get("date_to"))
        if date_from and date_to and date_from > date_to:
            date_from, date_to = date_to, date_from
        return cls(period, category, version, user_type, year_range, sort, date_from, date_to)

    def session_queryset(self):
        queryset = UserSession.objects.all()
        start, end = self.date_bounds()
        if start:
            queryset = queryset.filter(created_at__gte=start)
        if end:
            queryset = queryset.filter(created_at__lt=end)
        if self.category:
            queryset = queryset.filter(selected_category=self.category)
        if self.user_type == "authenticated":
            queryset = queryset.filter(user__isnull=False)
        elif self.user_type == "guest":
            queryset = queryset.filter(user__isnull=True)
        return queryset

    def date_bounds(self):
        now = timezone.now()
        if self.period == "all":
            return None, None
        if self.period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, start + timedelta(days=1)
        if self.period == "custom" and self.date_from:
            start = timezone.make_aware(timezone.datetime.combine(self.date_from, timezone.datetime.min.time()))
            end_date = self.date_to or self.date_from
            end = timezone.make_aware(timezone.datetime.combine(end_date + timedelta(days=1), timezone.datetime.min.time()))
            return start, end
        days = 30 if self.period == "30d" else 7
        return now - timedelta(days=days), None


def _parse_date(value):
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _feedback_summary(feedbacks):
    data = feedbacks.aggregate(
        count=Count("id"),
        average=Avg("rating"),
        positive=Count("id", filter=Q(rating__gte=4)),
        negative=Count("id", filter=Q(rating__lte=2)),
    )
    count = data["count"] or 0
    return {
        "feedback_count": count,
        "average_rating": data["average"] or 0,
        "positive_rate": percentage(data["positive"] or 0, count),
        "negative_rate": percentage(data["negative"] or 0, count),
    }


def recommendation_dashboard(filters, page_number=1):
    sessions = filters.session_queryset()
    results = RecommendationResult.objects.filter(session__in=sessions)
    if filters.version:
        results = results.filter(algorithm_version=filters.version)
    feedbacks = RecommendationFeedback.objects.filter(recommendation_result__in=results)
    session_count = sessions.count()
    completed_count = sessions.filter(completed_at__isnull=False).count()
    summary = _feedback_summary(feedbacks)
    result_count = results.count()
    metrics = {
        "user_count": sessions.filter(user__isnull=False).values("user_id").distinct().count(),
        "session_count": session_count,
        "completed_count": completed_count,
        "completion_rate": percentage(completed_count, session_count),
        "result_count": result_count,
        "coverage_rate": percentage(summary["feedback_count"], result_count),
        **summary,
    }

    daily_sessions = dict(
        sessions.annotate(day=TruncDate("created_at")).values_list("day").annotate(count=Count("id"))
    )
    daily_feedback = dict(
        feedbacks.annotate(day=TruncDate("updated_at")).values_list("day").annotate(count=Count("id"))
    )
    days = sorted(set(daily_sessions) | set(daily_feedback))

    category_rows = []
    for code, label in CATEGORY_LABELS.items():
        category_sessions = sessions.filter(selected_category=code)
        category_results = results.filter(session__selected_category=code)
        category_feedbacks = feedbacks.filter(recommendation_result__session__selected_category=code)
        category_summary = _feedback_summary(category_feedbacks)
        category_rows.append({
            "code": code,
            "label": label,
            "session_count": category_sessions.count(),
            "result_count": category_results.count(),
            **category_summary,
        })

    rank_rows = []
    for label, minimum, maximum in (("Top1", 1, 1), ("Top2-5", 2, 5), ("Top6-10", 6, 10), ("Top11-20", 11, 20)):
        rank_results = results.filter(rank_order__range=(minimum, maximum))
        rank_feedbacks = feedbacks.filter(recommendation_result__rank_order__range=(minimum, maximum))
        row = _feedback_summary(rank_feedbacks)
        row.update({"label": label, "result_count": rank_results.count(), "coverage_rate": percentage(row["feedback_count"], rank_results.count())})
        rank_rows.append(row)

    rank_points = []
    for rank in range(1, 21):
        rank_data = feedbacks.filter(recommendation_result__rank_order=rank).aggregate(average=Avg("rating"), count=Count("id"))
        rank_points.append({"rank": rank, "average": rank_data["average"] or 0, "count": rank_data["count"]})

    version_rows = []
    versions = results.values_list("algorithm_version", flat=True).distinct().order_by("algorithm_version")
    for version in versions:
        version_results = results.filter(algorithm_version=version)
        version_feedbacks = feedbacks.filter(recommendation_result__algorithm_version=version)
        row = _feedback_summary(version_feedbacks)
        row.update({"label": version, "result_count": version_results.count(), "coverage_rate": percentage(row["feedback_count"], version_results.count())})
        version_rows.append(row)

    movie_rows = (
        Movie.objects.filter(recommendation_results__in=results)
        .annotate(
            recommendation_count=Count("recommendation_results", distinct=True),
            feedback_count=Count("recommendation_results__feedback", distinct=True),
            average_feedback=Avg("recommendation_results__feedback__rating"),
            positive_count=Count("recommendation_results__feedback", filter=Q(recommendation_results__feedback__rating__gte=4), distinct=True),
        )
        .order_by("-recommendation_count", "title")
    )
    movie_page = Paginator(movie_rows, 10).get_page(page_number)
    for movie in movie_page.object_list:
        movie.coverage_rate = percentage(movie.feedback_count, movie.recommendation_count)
        movie.positive_rate = percentage(movie.positive_count, movie.feedback_count)

    distribution = dict(feedbacks.values_list("rating").annotate(count=Count("id")))
    return {
        "metrics": metrics,
        "trend_data": {"labels": [day.isoformat() for day in days], "series": [{"values": [daily_sessions.get(day, 0) for day in days], "color": "#c4642a"}, {"values": [daily_feedback.get(day, 0) for day in days], "color": "#3a7a50"}]},
        "funnel_data": [session_count, sessions.annotate(rating_count=Count("ratings")).filter(rating_count__gte=8).count(), completed_count, sessions.filter(recommendation_results__feedback__isnull=False).distinct().count()],
        "user_type_data": {"values": [sessions.filter(user__isnull=False).count(), sessions.filter(user__isnull=True).count()], "colors": ["#3a7a50", "#9a9087"]},
        "category_rows": category_rows,
        "rank_rows": rank_rows,
        "rank_points": rank_points,
        "rank_chart": {"labels": [row["rank"] for row in rank_points], "values": [row["average"] for row in rank_points]},
        "version_rows": version_rows,
        "feedback_distribution": [distribution.get(value, 0) for value in range(1, 6)],
        "feedback_chart": {"labels": ["1分", "2分", "3分", "4分", "5分"], "values": [distribution.get(value, 0) for value in range(1, 6)], "colors": ["#b84c4c", "#b84c4c", "#a87820", "#3a7a50", "#3a7a50"]},
        "category_session_chart": {"labels": [row["label"] for row in category_rows], "values": [row["session_count"] for row in category_rows]},
        "category_effect_chart": {"labels": [row["label"] for row in category_rows], "series": [{"values": [row["average_rating"] for row in category_rows], "color": "#c4642a"}, {"values": [row["positive_rate"] / 20 for row in category_rows], "color": "#3a7a50"}]},
        "movie_page": movie_page,
    }


def user_dashboard(filters, page_number=1):
    sessions = filters.session_queryset()
    authenticated = sessions.filter(user__isnull=False)
    guests = sessions.filter(user__isnull=True)
    start, end = filters.date_bounds()
    new_users = get_user_model().objects.all()
    if start:
        new_users = new_users.filter(date_joined__gte=start)
    if end:
        new_users = new_users.filter(date_joined__lt=end)
    duration = ExpressionWrapper(F("completed_at") - F("created_at"), output_field=DurationField())
    average_duration = sessions.filter(completed_at__isnull=False).annotate(duration=duration).aggregate(value=Avg("duration"))["value"]
    metrics = {
        "active_user_count": authenticated.values("user_id").distinct().count(),
        "new_user_count": new_users.count(),
        "session_count": sessions.count(),
        "authenticated_session_count": authenticated.count(),
        "guest_session_count": guests.count(),
        "sessions_per_user": authenticated.count() / max(1, authenticated.values("user_id").distinct().count()),
        "ratings_per_session": UserRating.objects.filter(session__in=sessions).count() / max(1, sessions.count()),
        "average_duration_seconds": average_duration.total_seconds() if average_duration else 0,
    }
    user_rows = (
        get_user_model().objects.filter(rating_sessions__in=sessions)
        .annotate(
            session_count=Count("rating_sessions", distinct=True),
            rating_count=Count("rating_sessions__ratings", distinct=True),
            feedback_count=Count("rating_sessions__recommendation_results__feedback", distinct=True),
            average_feedback=Avg("rating_sessions__recommendation_results__feedback__rating"),
            last_activity=F("last_login"),
        )
        .order_by("-session_count", "username")
    )
    user_page = Paginator(user_rows, 10).get_page(page_number)

    preference_dist = dict(UserRating.objects.filter(session__in=sessions).values_list("rating").annotate(count=Count("id")))
    preference_feedback = []
    for value in range(1, 6):
        session_ids = sessions.filter(ratings__rating=value).values("id")
        average = RecommendationFeedback.objects.filter(
            recommendation_result__session_id__in=session_ids
        ).aggregate(value=Avg("rating"))["value"] or 0
        preference_feedback.append(float(average))
    migration = {code: {target: 0 for target in CATEGORY_LABELS} for code in CATEGORY_LABELS}
    for user_id in authenticated.values_list("user_id", flat=True).distinct():
        categories = list(authenticated.filter(user_id=user_id).order_by("created_at").values_list("selected_category", flat=True))
        for source, target in zip(categories, categories[1:]):
            migration[source][target] += 1

    now = timezone.now()
    retained_7 = retained_30 = eligible_7 = eligible_30 = 0
    for user_id in authenticated.values_list("user_id", flat=True).distinct():
        completed = list(UserSession.objects.filter(user_id=user_id, completed_at__isnull=False).order_by("completed_at").values_list("completed_at", flat=True))
        if not completed:
            continue
        first = completed[0]
        if first <= now - timedelta(days=7):
            eligible_7 += 1
            retained_7 += any(first < value <= first + timedelta(days=7) for value in completed[1:])
        if first <= now - timedelta(days=30):
            eligible_30 += 1
            retained_30 += any(first < value <= first + timedelta(days=30) for value in completed[1:])

    return {
        "metrics": metrics,
        "user_page": user_page,
        "preference_distribution": [preference_dist.get(value, 0) for value in range(1, 6)],
        "preference_chart": {"labels": ["1分", "2分", "3分", "4分", "5分"], "values": [preference_dist.get(value, 0) for value in range(1, 6)]},
        "preference_feedback_chart": {"labels": ["偏好1", "偏好2", "偏好3", "偏好4", "偏好5"], "values": preference_feedback},
        "user_type_data": {"values": [authenticated.count(), guests.count()], "colors": ["#3a7a50", "#9a9087"]},
        "retention": {
            "seven_day": percentage(retained_7, eligible_7),
            "thirty_day": percentage(retained_30, eligible_30),
        },
        "migration_rows": [{"label": CATEGORY_LABELS[code], "values": list(migration[code].values())} for code in CATEGORY_LABELS],
    }


def _apply_year_filter(queryset, year_range):
    if year_range == "2020":
        return queryset.filter(year__gte=2020)
    if year_range in {"2010", "2000", "1990"}:
        start = int(year_range)
        return queryset.filter(year__gte=start, year__lte=start + 9)
    if year_range == "pre1990":
        return queryset.filter(year__lt=1990)
    return queryset


def movie_dashboard(filters, page_number=1):
    movies = Movie.objects.all()
    if filters.category:
        movies = movies.filter(main_category=filters.category)
    movies = _apply_year_filter(movies, filters.year_range)
    rows = movies.annotate(
        recommendation_count=Count("recommendation_results", distinct=True),
        feedback_count=Count("recommendation_results__feedback", distinct=True),
        average_feedback=Avg("recommendation_results__feedback__rating"),
        positive_count=Count("recommendation_results__feedback", filter=Q(recommendation_results__feedback__rating__gte=4), distinct=True),
        negative_count=Count("recommendation_results__feedback", filter=Q(recommendation_results__feedback__rating__lte=2), distinct=True),
    ).annotate(
        coverage_ratio=Case(
            When(recommendation_count=0, then=Value(0.0)),
            default=ExpressionWrapper(
                F("feedback_count") * 1.0 / F("recommendation_count"),
                output_field=FloatField(),
            ),
            output_field=FloatField(),
        )
    )
    ordering = {"recommendations": "-recommendation_count", "average_rating": "-average_feedback", "coverage": "-coverage_ratio"}[filters.sort]
    rows = rows.order_by(ordering, "title")
    movie_page = Paginator(rows, 20).get_page(page_number)
    for movie in movie_page.object_list:
        movie.coverage_rate = percentage(movie.feedback_count, movie.recommendation_count)
        movie.positive_rate = percentage(movie.positive_count, movie.feedback_count)

    all_rows = list(rows)
    for movie in all_rows:
        movie.coverage_rate = percentage(movie.feedback_count, movie.recommendation_count)
    qualified = [movie for movie in all_rows if movie.feedback_count >= 3]
    high = sorted(qualified, key=lambda movie: (movie.average_feedback or 0, movie.feedback_count), reverse=True)[:5]
    low = sorted(qualified, key=lambda movie: (movie.average_feedback or 0, -movie.feedback_count))[:5]
    high_exposure_low_feedback = sorted(
        [movie for movie in all_rows if movie.recommendation_count > 0],
        key=lambda movie: (-movie.recommendation_count, movie.coverage_rate),
    )[:5]
    high_feedback_low_exposure = sorted(
        qualified,
        key=lambda movie: (-(movie.average_feedback or 0), movie.recommendation_count),
    )[:5]
    category_counts = dict(movies.values_list("main_category").annotate(count=Count("id")))
    year_counts = dict(movies.exclude(year__isnull=True).values_list("year").annotate(count=Count("id")).order_by("year"))
    genres = Counter(); directors = Counter(); countries = Counter()
    for movie in movies.only("genres", "directors", "countries"):
        genres.update(movie.genres or [])
        directors.update(movie.directors or [])
        countries.update(movie.countries or [])
    total_recommendations = sum(movie.recommendation_count for movie in all_rows)
    total_feedbacks = sum(movie.feedback_count for movie in all_rows)
    positive = sum(movie.positive_count for movie in all_rows)
    negative = sum(movie.negative_count for movie in all_rows)
    return {
        "metrics": {
            "movie_count": len(all_rows),
            "recommended_movie_count": sum(movie.recommendation_count > 0 for movie in all_rows),
            "feedback_movie_count": sum(movie.feedback_count > 0 for movie in all_rows),
            "average_recommendations": total_recommendations / max(1, sum(movie.recommendation_count > 0 for movie in all_rows)),
            "average_douban_rating": movies.aggregate(value=Avg("rating"))["value"] or 0,
            "positive_negative_ratio": positive / max(1, negative),
            "feedback_count": total_feedbacks,
        },
        "movie_page": movie_page,
        "high_satisfaction": high,
        "low_satisfaction": low,
        "high_exposure_low_feedback": high_exposure_low_feedback,
        "high_feedback_low_exposure": high_feedback_low_exposure,
        "category_data": {"labels": [CATEGORY_LABELS[code] for code in CATEGORY_LABELS], "values": [category_counts.get(code, 0) for code in CATEGORY_LABELS]},
        "year_data": {"labels": list(year_counts), "values": list(year_counts.values())},
        "scatter_data": [{"title": movie.title, "x": movie.recommendation_count, "y": float(movie.average_feedback or 0), "r": max(4, min(18, movie.feedback_count + 4))} for movie in all_rows if movie.recommendation_count],
        "scatter_chart": {"points": [{"title": movie.title, "x": movie.recommendation_count, "y": float(movie.average_feedback or 0), "r": max(4, min(18, movie.feedback_count + 4))} for movie in all_rows if movie.recommendation_count]},
        "diversity": {"genres": genres.most_common(8), "directors": directors.most_common(8), "countries": countries.most_common(8)},
    }


def data_quality_dashboard():
    movies = list(Movie.objects.all())
    quality = {
        "missing_poster": sum(not movie.poster_url for movie in movies),
        "missing_summary": sum(not movie.summary for movie in movies),
        "missing_directors": sum(not movie.directors for movie in movies),
        "missing_actors": sum(not movie.actors for movie in movies),
        "missing_tags": sum(not movie.feature_tags for movie in movies),
        "missing_douban_id": sum(not movie.douban_id for movie in movies),
    }
    category_counts = Counter(movie.main_category for movie in movies)
    rating_buckets = [0] * 10
    for movie in movies:
        index = min(9, max(0, int(float(movie.rating))))
        rating_buckets[index] += 1
    sync_rows = []
    for source in (SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION):
        latest = SyncRun.objects.filter(source=source).first()
        sync_rows.append({"source": source, "label": SyncRun.Source(source).label, "latest": latest})
    return {
        "metrics": {
            "chart_count": DoubanChartMovie.objects.filter(is_active=True).count(),
            "weekly_count": DoubanWeeklyReputationMovie.objects.filter(is_active=True).count(),
            "news_count": UpcomingMovieNews.objects.filter(is_active=True).count(),
            "movie_count": len(movies),
            "form_count": RatingForm.objects.filter(is_active=True).count(),
        },
        "quality": quality,
        "sync_rows": sync_rows,
        "sync_history": SyncRun.objects.select_related("triggered_by")[:20],
        "category_data": {"labels": [CATEGORY_LABELS[code] for code in CATEGORY_LABELS], "values": [category_counts.get(code, 0) for code in CATEGORY_LABELS]},
        "rating_data": {"labels": [f"{value}-{value + 1}" for value in range(10)], "values": rating_buckets},
        "upcoming_news": UpcomingMovieNews.objects.filter(is_active=True).order_by("event_date")[:12],
    }
