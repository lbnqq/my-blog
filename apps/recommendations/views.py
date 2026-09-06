from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.blog.services.douban_chart import sync_douban_chart
from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.recommendations.models import RecommendationResult, SyncRun
from apps.recommendations.services.analytics import (
    AnalyticsFilters,
    data_quality_dashboard,
    movie_dashboard,
    recommendation_dashboard,
    user_dashboard,
)


def staff_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def common_context(request, active_page, filters=None):
    return {
        "active_page": active_page,
        "filters": filters,
        "category_labels": CATEGORY_LABELS,
        "algorithm_versions": RecommendationResult.objects.values_list(
            "algorithm_version", flat=True
        ).distinct().order_by("algorithm_version"),
        "query_string": request.GET.urlencode(),
        "updated_at": timezone.now(),
    }


@staff_required
def analytics_center(request):
    context = common_context(request, "center")
    context.update(data_quality_dashboard()["metrics"])
    return render(request, "recommendations/analytics_center.html", context)


@staff_required
def recommendation_analytics(request):
    filters = AnalyticsFilters.from_request(request)
    context = common_context(request, "recommendations", filters)
    context.update(recommendation_dashboard(filters, request.GET.get("page", 1)))
    return render(request, "recommendations/analytics_recommendations.html", context)


@staff_required
def user_analytics(request):
    filters = AnalyticsFilters.from_request(request)
    context = common_context(request, "users", filters)
    context.update(user_dashboard(filters, request.GET.get("page", 1)))
    return render(request, "recommendations/analytics_users.html", context)


@staff_required
def movie_analytics(request):
    filters = AnalyticsFilters.from_request(request)
    context = common_context(request, "movies", filters)
    context.update(movie_dashboard(filters, request.GET.get("page", 1)))
    return render(request, "recommendations/analytics_movies.html", context)


@staff_required
def data_quality(request):
    context = common_context(request, "data_quality")
    context.update(data_quality_dashboard())
    return render(request, "recommendations/analytics_data_quality.html", context)


SYNC_SOURCES = {SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION}


def sync_handler(source):
    if source == SyncRun.Source.DOUBAN_CHART:
        return sync_douban_chart
    if source == SyncRun.Source.WEEKLY_REPUTATION:
        return sync_douban_weekly_reputation
    raise ValueError("Unknown sync source")


def execute_sync(source, user):
    handler = sync_handler(source)
    run = SyncRun.objects.create(
        source=source,
        status=SyncRun.Status.RUNNING,
        triggered_by=user,
    )
    try:
        result = handler(force=True)
        status = {
            "updated": SyncRun.Status.SUCCESS,
            "skipped": SyncRun.Status.SKIPPED,
            "failed": SyncRun.Status.FAILED,
        }.get(result.status, SyncRun.Status.FAILED)
        run.status = status
        run.updated_count = result.updated_count
        run.message = result.message
    except Exception as exc:
        run.status = SyncRun.Status.FAILED
        run.message = str(exc)
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "updated_count", "message", "finished_at"])
    return run


@staff_required
@require_POST
def sync_data(request, source):
    if source not in SYNC_SOURCES:
        raise PermissionDenied
    run = execute_sync(source, request.user)
    if run.status == SyncRun.Status.FAILED:
        messages.error(request, f"{run.get_source_display()}同步失败：{run.message}")
    else:
        messages.success(request, f"{run.get_source_display()}同步完成：{run.message}")
    return redirect("recommendations:data_quality")


@staff_required
@require_POST
def sync_all(request):
    runs = [execute_sync(source, request.user) for source in (SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION)]
    failed = sum(run.status == SyncRun.Status.FAILED for run in runs)
    if failed:
        messages.error(request, f"同步完成，其中 {failed} 个数据源失败。")
    else:
        messages.success(request, "豆瓣排行榜和一周口碑榜同步完成。")
    return redirect("recommendations:data_quality")
