from django.test import TestCase

from apps.movies.models import Movie
from apps.ratings.models import UserRating, UserSession
from apps.recommendations.models import RecommendationResult
from apps.recommendations.services.recommender import recommend_movies


class RecommenderTests(TestCase):
    def create_movie(self, index, category="suspense_crime", genres=None):
        return Movie.objects.create(
            douban_id=f"db{index}",
            title=f"电影{index}",
            original_title=f"Movie {index}",
            year=2000 + index % 20,
            directors=[f"导演{index}"],
            actors=[f"演员{index % 7}"],
            genres=genres or ["悬疑", "犯罪"],
            countries=["美国"],
            rating=8.0 + (index % 10) / 10,
            rating_count=100000 + index,
            rank=index,
            poster_url="",
            summary="一部包含悬疑和反转元素的电影",
            main_category=category,
            feature_tags=genres or ["悬疑", "犯罪", "反转"],
        )

    def test_recommend_movies_excludes_rated_and_saves_results(self):
        rated_a = self.create_movie(1)
        rated_b = self.create_movie(2)
        for index in range(3, 30):
            self.create_movie(index)

        session = UserSession.objects.create(selected_category="suspense_crime")
        UserRating.objects.create(session=session, movie=rated_a, rating=5)
        UserRating.objects.create(session=session, movie=rated_b, rating=4)

        results = recommend_movies(session)

        self.assertEqual(len(results), 20)
        result_ids = {result.movie_id for result in results}
        self.assertNotIn(rated_a.id, result_ids)
        self.assertNotIn(rated_b.id, result_ids)
        self.assertEqual(RecommendationResult.objects.filter(session=session).count(), 20)
        self.assertEqual(results[0].rank_order, 1)
        self.assertGreaterEqual(results[0].score, results[-1].score)
