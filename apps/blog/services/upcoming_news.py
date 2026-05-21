import datetime

from django.utils import timezone

from apps.blog.models import UpcomingMovieNews


def _select_upcoming_items(queryset, today, limit):
    week_end = today + datetime.timedelta(days=7)
    future_queryset = queryset.filter(event_date__gte=today).order_by("event_date", "sort_order", "title")
    this_week = list(future_queryset.filter(event_date__lte=week_end)[:limit])
    if len(this_week) >= limit:
        return this_week

    selected_ids = [item.id for item in this_week]
    later = list(future_queryset.exclude(id__in=selected_ids)[: limit - len(this_week)])
    selected_ids += [item.id for item in later]
    if len(this_week) + len(later) >= limit:
        return this_week + later

    recent_start = today - datetime.timedelta(days=7)
    recent_past = list(
        queryset.filter(event_date__gte=recent_start, event_date__lt=today)
        .exclude(id__in=selected_ids)
        .order_by("-event_date", "sort_order", "title")[: limit - len(this_week) - len(later)]
    )
    return this_week + later + recent_past


def get_homepage_upcoming_news(today=None, limit=5):
    today = today or timezone.localdate()
    base_queryset = UpcomingMovieNews.objects.filter(
        is_active=True,
        content_type=UpcomingMovieNews.ContentType.UPCOMING,
    )
    return _select_upcoming_items(base_queryset, today, limit)


def get_homepage_upcoming_groups(today=None, per_region=3):
    today = today or timezone.localdate()
    base_queryset = UpcomingMovieNews.objects.filter(
        is_active=True,
        content_type=UpcomingMovieNews.ContentType.UPCOMING,
    )
    domestic = _select_upcoming_items(
        base_queryset.filter(region=UpcomingMovieNews.Region.DOMESTIC),
        today,
        per_region,
    )
    foreign = _select_upcoming_items(
        base_queryset.filter(region=UpcomingMovieNews.Region.FOREIGN),
        today,
        per_region,
    )
    return domestic, foreign


def get_homepage_now_showing(today=None, limit=6):
    return list(
        UpcomingMovieNews.objects.filter(
            is_active=True,
            content_type=UpcomingMovieNews.ContentType.NOW_SHOWING,
        ).order_by("sort_order", "-event_date", "title")[:limit]
    )
