from collections import OrderedDict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Avg, Count, Q
from django.shortcuts import render

from apps.recommendations.models import RecommendationFeedback, RecommendationResult


RANK_BUCKETS = OrderedDict(
    [
        ("Top1", (1, 1)),
        ("Top2-5", (2, 5)),
        ("Top6-10", (6, 10)),
        ("Top11-20", (11, 20)),
    ]
)


def percentage(part, total):
    return part / total * 100 if total else 0.0


def build_group_row(label, results, feedbacks):
    total_count = results.count()
    feedback_summary = feedbacks.aggregate(
        feedback_count=Count("id"),
        average_rating=Avg("rating"),
        positive_count=Count("id", filter=Q(rating__gte=4)),
        negative_count=Count("id", filter=Q(rating__lte=2)),
    )
    feedback_count = feedback_summary["feedback_count"]
    return {
        "label": label,
        "total_count": total_count,
        "feedback_count": feedback_count,
        "coverage_rate": percentage(feedback_count, total_count),
        "average_rating": feedback_summary["average_rating"] or 0.0,
        "positive_rate": percentage(feedback_summary["positive_count"], feedback_count),
        "negative_rate": percentage(feedback_summary["negative_count"], feedback_count),
    }


@login_required
def recommendation_analytics(request):
    if not request.user.is_staff:
        raise PermissionDenied

    results = RecommendationResult.objects.all()
    feedbacks = RecommendationFeedback.objects.all()
    metrics = build_group_row("All", results, feedbacks)

    rank_rows = []
    for label, (minimum, maximum) in RANK_BUCKETS.items():
        rank_rows.append(
            build_group_row(
                label,
                results.filter(rank_order__gte=minimum, rank_order__lte=maximum),
                feedbacks.filter(
                    recommendation_result__rank_order__gte=minimum,
                    recommendation_result__rank_order__lte=maximum,
                ),
            )
        )

    algorithm_rows = []
    for version in results.values_list("algorithm_version", flat=True).distinct().order_by("algorithm_version"):
        algorithm_rows.append(
            build_group_row(
                version,
                results.filter(algorithm_version=version),
                feedbacks.filter(recommendation_result__algorithm_version=version),
            )
        )

    category_rows = []
    for category in results.values_list("session__selected_category", flat=True).distinct().order_by(
        "session__selected_category"
    ):
        category_rows.append(
            build_group_row(
                category,
                results.filter(session__selected_category=category),
                feedbacks.filter(recommendation_result__session__selected_category=category),
            )
        )

    return render(
        request,
        "recommendations/analytics.html",
        {
            "metrics": metrics,
            "rank_rows": rank_rows,
            "algorithm_rows": algorithm_rows,
            "category_rows": category_rows,
        },
    )
