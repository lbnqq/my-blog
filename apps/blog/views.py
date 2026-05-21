from django.shortcuts import get_object_or_404, render

from apps.blog.models import UpcomingMovieNews
from apps.blog.services.upcoming_news import get_homepage_now_showing, get_homepage_upcoming_groups
from apps.movies.services.daily_movie import get_daily_movie


def home(request):
    daily_movie = get_daily_movie()
    upcoming_domestic, upcoming_foreign = get_homepage_upcoming_groups(per_region=3)
    now_showing_movies = get_homepage_now_showing(limit=6)
    return render(
        request,
        "blog/home.html",
        {
            "daily_movie": daily_movie,
            "upcoming_domestic": upcoming_domestic,
            "upcoming_foreign": upcoming_foreign,
            "now_showing_movies": now_showing_movies,
        },
    )


def news_detail(request, pk):
    news = get_object_or_404(UpcomingMovieNews, pk=pk, is_active=True)
    return render(request, "blog/news_detail.html", {"news": news})
