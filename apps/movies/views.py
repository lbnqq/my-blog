from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.blog.services.poster_fetcher import fetch_douban_poster
from apps.movies.models import Movie
from apps.movies.services.daily_movie import get_related_movies
from apps.movies.templatetags.movie_posters import poster_cache_path


def fetch_movie_poster(movie):
    return fetch_douban_poster(
        movie.poster_url,
        f"https://movie.douban.com/subject/{movie.douban_id}/",
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
    except (OSError, TimeoutError) as exc:
        raise Http404("Movie poster could not be loaded.") from exc
    target_path = poster_cache_path(movie)
    if target_path is not None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content)
    response = HttpResponse(content, content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response
