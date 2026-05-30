import urllib.error
import urllib.request

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.movies.models import Movie
from apps.movies.services.daily_movie import get_related_movies


def fetch_movie_poster(movie):
    request = urllib.request.Request(
        movie.poster_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://movie.douban.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return response.read(), content_type


def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    related_movies = get_related_movies(movie, limit=4)
    return render(
        request,
        "movies/detail.html",
        {
            "movie": movie,
            "related_movies": related_movies,
        },
    )


def movie_poster(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    if not movie.poster_url:
        raise Http404("Movie poster is missing.")
    try:
        content, content_type = fetch_movie_poster(movie)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        raise Http404("Movie poster could not be loaded.") from exc
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response
