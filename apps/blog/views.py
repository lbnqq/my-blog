import urllib.error

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie, UpcomingMovieNews
from apps.blog.services.douban_chart import fetch_douban_chart_poster, get_homepage_douban_chart
from apps.blog.services.douban_weekly_reputation import (
    fetch_douban_weekly_reputation_poster,
    get_homepage_weekly_reputation,
)
from apps.movies.services.daily_movie import get_daily_movie


def home(request):
    daily_movie = get_daily_movie()
    weekly_reputation_movies = get_homepage_weekly_reputation(limit=6)
    douban_chart_movies = get_homepage_douban_chart(limit=6)
    return render(
        request,
        "blog/home.html",
        {
            "daily_movie": daily_movie,
            "weekly_reputation_movies": weekly_reputation_movies,
            "douban_chart_movies": douban_chart_movies,
        },
    )


def news_detail(request, pk):
    news = get_object_or_404(UpcomingMovieNews, pk=pk, is_active=True)
    return render(request, "blog/news_detail.html", {"news": news})


def douban_chart_poster(request, douban_id):
    movie = get_object_or_404(DoubanChartMovie, douban_id=douban_id, is_active=True)
    if not movie.poster_url:
        raise Http404("Douban chart poster is missing.")
    try:
        content, content_type = fetch_douban_chart_poster(movie)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise Http404("Douban chart poster could not be loaded.") from exc
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response


def douban_weekly_reputation_poster(request, douban_id):
    movie = get_object_or_404(DoubanWeeklyReputationMovie, douban_id=douban_id, is_active=True)
    if not movie.poster_url:
        raise Http404("Douban weekly reputation poster is missing.")
    try:
        content, content_type = fetch_douban_weekly_reputation_poster(movie)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise Http404("Douban weekly reputation poster could not be loaded.") from exc
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response
