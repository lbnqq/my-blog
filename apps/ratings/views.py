from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.movies.services.classifier import CATEGORY_LABELS
from apps.ratings.forms import CategorySelectionForm
from apps.ratings.models import UserRating, UserSession
from apps.ratings.services.rating_form_service import get_active_form_for_category
from apps.ratings.services.session_service import create_user_session
from apps.recommendations.services.recommender import recommend_movies


def select_category(request):
    if request.method == "POST":
        form = CategorySelectionForm(request.POST)
        if form.is_valid():
            session = create_user_session(form.cleaned_data["category"])
            return redirect(reverse("ratings:rate", args=[session.session_key]))
    else:
        form = CategorySelectionForm()

    return render(
        request,
        "ratings/select_category.html",
        {"form": form, "category_labels": CATEGORY_LABELS},
    )


def rate_movies(request, session_key):
    session = get_object_or_404(UserSession, session_key=session_key)
    rating_form = get_active_form_for_category(session.selected_category)
    form_movies = list(rating_form.form_movies.all()) if rating_form else []

    if request.method == "POST":
        ratings = {}
        for form_movie in form_movies:
            value = request.POST.get(f"movie_{form_movie.movie_id}")
            if value:
                ratings[form_movie.movie] = int(value)

        if len(ratings) < 8:
            messages.error(request, "请至少评价 8 部电影后再提交。")
        else:
            UserRating.objects.filter(session=session).delete()
            UserRating.objects.bulk_create(
                [
                    UserRating(session=session, movie=movie, rating=rating)
                    for movie, rating in ratings.items()
                ]
            )
            recommend_movies(session)
            return redirect(reverse("ratings:result", args=[session.session_key]))

    return render(
        request,
        "ratings/rating_form.html",
        {
            "session": session,
            "rating_form": rating_form,
            "form_movies": form_movies,
            "category_label": CATEGORY_LABELS.get(session.selected_category, ""),
            "rating_values": [1, 2, 3, 4, 5],
        },
    )


def recommendation_result(request, session_key):
    session = get_object_or_404(UserSession, session_key=session_key)
    results = session.recommendation_results.select_related("movie").order_by("rank_order")
    return render(
        request,
        "recommendations/result.html",
        {
            "session": session,
            "results": results,
            "category_label": CATEGORY_LABELS.get(session.selected_category, ""),
        },
    )
