from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from apps.movies.services.classifier import CATEGORY_LABELS
from apps.ratings.models import UserSession
from apps.recommendations.models import RecommendationResult
from apps.recommendations.services.feedback import attach_feedback_ratings, save_recommendation_feedback


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("blog:home")
    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def recommendation_history(request):
    sessions = list(
        UserSession.objects.filter(user=request.user)
        .annotate(rating_count=Count("ratings"))
        .prefetch_related(
            Prefetch(
                "recommendation_results",
                queryset=RecommendationResult.objects.select_related("movie").order_by("rank_order"),
            )
        )
        .order_by("-created_at")
    )
    for session in sessions:
        session.category_label = CATEGORY_LABELS.get(session.selected_category, session.selected_category)
    return render(
        request,
        "accounts/recommendation_history.html",
        {"sessions": sessions},
    )


@login_required
def recommendation_history_detail(request, session_key):
    session = get_object_or_404(
        UserSession.objects.filter(user=request.user)
        .prefetch_related("ratings__movie", "recommendation_results__movie"),
        session_key=session_key,
    )
    ratings = session.ratings.select_related("movie").order_by("created_at")
    results = list(
        session.recommendation_results.select_related("movie").prefetch_related("feedback").order_by("rank_order")
    )
    attach_feedback_ratings(results)

    if request.method == "POST":
        saved_count = save_recommendation_feedback(request.POST, results)
        if saved_count:
            messages.success(request, f"已保存 {saved_count} 条推荐反馈。")
        return redirect("accounts:recommendation_history_detail", session_key=session.session_key)

    return render(
        request,
        "accounts/recommendation_history_detail.html",
        {
            "session": session,
            "ratings": ratings,
            "results": results,
            "category_label": CATEGORY_LABELS.get(session.selected_category, ""),
            "rating_values": [1, 2, 3, 4, 5],
        },
    )
