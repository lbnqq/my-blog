import datetime

from django.utils import timezone

from apps.movies.models import Movie


ANCHOR_DATE = datetime.date(2026, 5, 18)


def get_daily_movie(today=None):
    today = today or timezone.localdate()
    movies = list(Movie.objects.filter(rank__lte=100).order_by("rank", "-rating", "title"))
    if not movies:
        movies = list(Movie.objects.order_by("rank", "-rating", "title"))
    if not movies:
        return None

    offset = (today - ANCHOR_DATE).days
    return movies[offset % len(movies)]


def get_related_movies(movie, limit=4):
    if movie is None:
        return []

    shared_genres = list(movie.genres or [])
    candidates = list(Movie.objects.exclude(pk=movie.pk))

    def score(candidate):
        candidate_genres = set(candidate.genres or [])
        shared_count = len(set(shared_genres) & candidate_genres)
        same_category = candidate.main_category == movie.main_category
        rank_value = candidate.rank or 99999
        return (-int(same_category), -shared_count, rank_value, -float(candidate.rating), candidate.title)

    sorted_candidates = sorted(candidates, key=score)
    return [
        candidate
        for candidate in sorted_candidates
        if candidate.main_category == movie.main_category
        or set(shared_genres) & set(candidate.genres or [])
    ][:limit]
