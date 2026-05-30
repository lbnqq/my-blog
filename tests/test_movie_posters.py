from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.movies.models import Movie


class MoviePosterTests(TestCase):
    def make_movie(self):
        return Movie.objects.create(
            douban_id="1292052",
            title="肖申克的救赎",
            original_title="The Shawshank Redemption",
            year=1994,
            directors=["弗兰克·德拉邦特"],
            actors=["蒂姆·罗宾斯", "摩根·弗里曼"],
            genres=["剧情", "犯罪"],
            countries=["美国"],
            rating="9.7",
            rating_count=3000000,
            rank=1,
            poster_url="https://img3.doubanio.com/view/photo/s_ratio_poster/public/p480747492.webp",
            summary="测试简介",
            main_category="suspense_crime",
            feature_tags=["剧情", "犯罪"],
        )

    @override_settings(STATICFILES_DIRS=[settings.BASE_DIR / "tests" / "fixtures" / "static"])
    def test_homepage_uses_cached_local_poster_when_available(self):
        movie = self.make_movie()
        poster_path = Path(settings.STATICFILES_DIRS[0]) / "img" / "posters"
        poster_path.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: (poster_path / "1292052.webp").unlink(missing_ok=True))
        (poster_path / "1292052.webp").write_bytes(b"poster")

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, 'src="/static/img/posters/1292052.webp"')
        self.assertNotContains(response, '<div class="poster-fallback">肖申克的救赎</div>')

    @override_settings(STATICFILES_DIRS=[settings.BASE_DIR / "tests" / "fixtures" / "static"])
    def test_detail_page_uses_proxy_poster_when_cached_poster_is_missing(self):
        movie = self.make_movie()

        response = self.client.get(reverse("movies:detail", args=[movie.pk]))

        self.assertContains(response, reverse("movies:poster", args=[movie.pk]))
        self.assertContains(response, '<div class="poster-fallback is-hidden">肖申克的救赎</div>')

    @override_settings(STATICFILES_DIRS=[settings.BASE_DIR / "tests" / "fixtures" / "static"])
    def test_homepage_uses_proxy_poster_when_cached_poster_is_missing(self):
        movie = self.make_movie()

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, reverse("movies:poster", args=[movie.pk]))
        self.assertContains(response, '<div class="poster-fallback is-hidden">肖申克的救赎</div>')

    def test_movie_poster_proxy_streams_remote_poster(self):
        movie = self.make_movie()

        with patch("apps.movies.views.fetch_movie_poster", return_value=(b"poster-bytes", "image/webp")):
            response = self.client.get(reverse("movies:poster", args=[movie.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response.content, b"poster-bytes")
