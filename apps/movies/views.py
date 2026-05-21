from django.shortcuts import get_object_or_404, render

from apps.movies.models import Movie
from apps.movies.services.daily_movie import get_related_movies


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
