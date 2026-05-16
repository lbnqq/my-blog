from decimal import Decimal

from django.test import TestCase

from apps.movies.models import Movie
from apps.ratings.models import RatingForm, RatingFormMovie
from apps.ratings.services.rating_form_builder import rebuild_rating_form


class RatingFormBuilderTests(TestCase):
    def create_movie(self, index, rating, rating_count, genre):
        return Movie.objects.create(
            douban_id=f"builder-{index}",
            title=f"Builder Movie {index}",
            original_title=f"Builder Movie {index}",
            year=2000 + index,
            directors=[f"Director {index}"],
            actors=[f"Actor {index}"],
            genres=[genre, "剧情"],
            countries=["中国"],
            rating=rating,
            rating_count=rating_count,
            rank=index,
            poster_url="",
            summary="Movie for rating form builder tests.",
            main_category="suspense_crime",
            feature_tags=[genre, "高分"],
        )

    def test_rebuild_rating_form_keeps_best_twenty_with_required_first_eight(self):
        low_quality_movie = self.create_movie(1, 7.1, 1000, "悬疑")
        for index in range(2, 27):
            genre = "犯罪" if index % 2 == 0 else "惊悚"
            self.create_movie(index, 8.0 + (index % 10) / 10, 100000 + index, genre)

        form = rebuild_rating_form("suspense_crime")

        links = list(RatingFormMovie.objects.filter(form=form).select_related("movie"))
        linked_movies = [link.movie for link in links]

        self.assertEqual(len(links), 20)
        self.assertNotIn(low_quality_movie, linked_movies)
        self.assertEqual([link.sort_order for link in links], list(range(1, 21)))
        self.assertEqual(sum(link.is_required for link in links), 8)
        self.assertTrue(all(link.is_required for link in links[:8]))
        self.assertEqual(linked_movies[0].rating, Decimal("8.9"))

    def test_rebuild_rating_form_replaces_stale_links(self):
        form = RatingForm.objects.create(
            category="suspense_crime",
            title="Old title",
            description="Old description",
        )
        stale_movie = self.create_movie(1, 7.0, 100, "悬疑")
        RatingFormMovie.objects.create(form=form, movie=stale_movie, sort_order=1, is_required=True)
        fresh_movie = self.create_movie(2, 9.1, 1000000, "犯罪")

        rebuilt_form = rebuild_rating_form("suspense_crime")

        self.assertEqual(rebuilt_form.id, form.id)
        links = list(RatingFormMovie.objects.filter(form=rebuilt_form))
        self.assertEqual(len(links), 2)
        self.assertEqual(links[0].movie, fresh_movie)
        self.assertEqual(links[1].movie, stale_movie)
