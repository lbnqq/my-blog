from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.ratings.models import RatingForm, RatingFormMovie


FORM_MOVIE_LIMIT = 20
REQUIRED_MOVIE_LIMIT = 8


def rebuild_all_rating_forms():
    return [rebuild_rating_form(category) for category in CATEGORY_LABELS]


def rebuild_rating_form(category, limit=FORM_MOVIE_LIMIT, required_limit=REQUIRED_MOVIE_LIMIT):
    form, _created = RatingForm.objects.update_or_create(
        category=category,
        defaults={
            "title": f"{CATEGORY_LABELS[category]}电影评分表",
            "description": f"根据你对{CATEGORY_LABELS[category]}类电影的评分生成推荐。",
            "is_active": True,
        },
    )

    selected_movies = select_representative_movies(category, limit)
    RatingFormMovie.objects.filter(form=form).delete()
    RatingFormMovie.objects.bulk_create(
        [
            RatingFormMovie(
                form=form,
                movie=movie,
                sort_order=index,
                is_required=index <= required_limit,
            )
            for index, movie in enumerate(selected_movies, start=1)
        ]
    )
    return form


def select_representative_movies(category, limit=FORM_MOVIE_LIMIT):
    movies = list(
        Movie.objects.filter(main_category=category).order_by(
            "-rating",
            "-rating_count",
            "rank",
            "title",
        )
    )
    if len(movies) <= limit:
        return movies

    quality_pool = movies[:limit]
    selected = []
    skipped = []
    seen_primary_genres = set()

    for movie in quality_pool:
        primary_genre = first_genre(movie)
        if primary_genre and primary_genre not in seen_primary_genres:
            selected.append(movie)
            seen_primary_genres.add(primary_genre)
        else:
            skipped.append(movie)

        if len(selected) == limit:
            return selected

    for movie in skipped:
        selected.append(movie)
        if len(selected) == limit:
            break

    return selected


def first_genre(movie):
    for genre in movie.genres or []:
        genre = str(genre).strip()
        if genre:
            return genre
    return ""
