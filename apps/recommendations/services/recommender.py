from collections import Counter, defaultdict

from django.db import transaction
from django.utils import timezone

from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.recommendations.models import RecommendationResult
from apps.recommendations.services.parameter_selector import choose_parameter_group
from apps.recommendations.services.reason_generator import generate_reason
from apps.recommendations.services.similarity import (
    jaccard_similarity,
    normalize_douban_rating,
    normalize_rank,
    year_similarity,
)


RATING_WEIGHTS = {
    5: 2.0,
    4: 1.0,
    3: 0.2,
    2: -1.0,
    1: -2.0,
}


def build_user_preference(ratings):
    preference = {
        "ratings": list(ratings),
        "rated_movie_ids": set(),
        "liked_movies": [],
        "disliked_movies": [],
        "tags": Counter(),
        "genres": Counter(),
    }

    for rating in ratings:
        movie = rating.movie
        weight = RATING_WEIGHTS.get(int(rating.rating), 0)
        preference["rated_movie_ids"].add(movie.id)
        if rating.rating >= 4:
            preference["liked_movies"].append(movie)
        elif rating.rating <= 2:
            preference["disliked_movies"].append(movie)

        for tag in movie.feature_tags:
            preference["tags"][tag] += weight
        for genre in movie.genres:
            preference["genres"][genre] += weight

    return preference


def calculate_movie_similarity(source_movie, candidate):
    genre_score = jaccard_similarity(source_movie.genres, candidate.genres)
    director_score = jaccard_similarity(source_movie.directors, candidate.directors)
    actor_score = jaccard_similarity(source_movie.actors, candidate.actors)
    country_score = jaccard_similarity(source_movie.countries, candidate.countries)
    tag_score = jaccard_similarity(source_movie.feature_tags, candidate.feature_tags)
    year_score = year_similarity(source_movie.year, candidate.year)

    return (
        0.40 * genre_score
        + 0.15 * director_score
        + 0.15 * actor_score
        + 0.10 * country_score
        + 0.10 * year_score
        + 0.10 * tag_score
    )


def calculate_similarity_score(preference, candidate):
    ratings = preference["ratings"]
    if not ratings:
        return 0.0, []

    total = 0.0
    source_scores = []
    shared_tags = set()
    for rating in ratings:
        weight = RATING_WEIGHTS.get(int(rating.rating), 0)
        similarity = calculate_movie_similarity(rating.movie, candidate)
        total += weight * similarity
        if rating.rating >= 4 and similarity > 0:
            source_scores.append((rating.movie.title, similarity))
            shared_tags.update(set(rating.movie.feature_tags) & set(candidate.feature_tags))

    confidence = min(1.0, len(ratings) / 12)
    tag_penalty = min(1.0, len(shared_tags) / 3) if shared_tags else 0.7
    adjusted = max(0.0, total / max(1, len(ratings))) * confidence * tag_penalty
    source_scores.sort(key=lambda item: item[1], reverse=True)
    return adjusted, [title for title, _score in source_scores[:2]]


def calculate_category_score(movie, selected_category):
    if movie.main_category == selected_category:
        return 1.0
    return 0.3 if set(movie.genres) & set(CATEGORY_LABELS.values()) else 0.0


def calculate_diversity_score(movie, selected_movies):
    if not selected_movies:
        return 1.0
    director_counts = defaultdict(int)
    genre_counts = defaultdict(int)
    for selected in selected_movies:
        for director in selected.directors:
            director_counts[director] += 1
        for genre in selected.genres:
            genre_counts[genre] += 1
    director_penalty = max((director_counts[d] for d in movie.directors), default=0)
    genre_penalty = max((genre_counts[g] for g in movie.genres), default=0)
    return max(0.0, 1.0 - director_penalty * 0.15 - genre_penalty * 0.04)


def score_candidate_movie(movie, session, preference, params, selected_movies=None):
    selected_movies = selected_movies or []
    similarity_score, source_titles = calculate_similarity_score(preference, movie)
    category_score = calculate_category_score(movie, session.selected_category)
    douban_score = normalize_douban_rating(movie.rating)
    popularity_score = normalize_rank(movie.rank)
    diversity_score = calculate_diversity_score(movie, selected_movies)

    final_score = (
        params.similarity_weight * similarity_score
        + params.category_weight * category_score
        + params.rating_weight * douban_score
        + params.popularity_weight * popularity_score
        + params.diversity_weight * diversity_score
    )
    if movie.main_category == session.selected_category:
        final_score *= 1.15

    shared_tags = [
        tag for tag, count in preference["tags"].most_common(5) if tag in movie.feature_tags and count > 0
    ]
    reason = generate_reason(
        movie.title,
        source_titles,
        shared_tags,
        CATEGORY_LABELS.get(session.selected_category, ""),
        movie.rating,
    )
    return final_score, reason


def apply_diversity_filter(scored_movies, limit=20):
    selected = []
    director_counts = Counter()
    for movie, score, reason in scored_movies:
        if any(director_counts[director] >= 3 for director in movie.directors):
            continue
        selected.append((movie, score, reason))
        for director in movie.directors:
            director_counts[director] += 1
        if len(selected) >= limit:
            break
    return selected


@transaction.atomic
def recommend_movies(session, limit=20):
    ratings = list(session.ratings.select_related("movie"))
    preference = build_user_preference(ratings)
    params = choose_parameter_group([rating.rating for rating in ratings])
    candidates = Movie.objects.exclude(id__in=preference["rated_movie_ids"])

    scored_movies = []
    for movie in candidates:
        score, reason = score_candidate_movie(movie, session, preference, params)
        scored_movies.append((movie, score, reason))

    scored_movies.sort(key=lambda item: item[1], reverse=True)
    selected = apply_diversity_filter(scored_movies, limit=limit)

    RecommendationResult.objects.filter(session=session).delete()
    results = []
    for index, (movie, score, reason) in enumerate(selected, start=1):
        results.append(
            RecommendationResult.objects.create(
                session=session,
                movie=movie,
                score=score,
                rank_order=index,
                reason=reason,
                algorithm_version="taskcf_v1",
            )
        )

    session.completed_at = timezone.now()
    session.save(update_fields=["completed_at"])
    return results
