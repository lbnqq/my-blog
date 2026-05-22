import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.movies.models import Movie


class MovieBlogHomepageTests(TestCase):
    def make_movie(self, index, **overrides):
        data = {
            "douban_id": f"daily-{index}",
            "title": f"Movie {index}",
            "original_title": f"Original {index}",
            "year": 2000 + index,
            "directors": [f"Director {index}"],
            "actors": [f"Actor {index}"],
            "genres": ["Drama", "Crime"] if index % 2 else ["Drama"],
            "countries": ["China"],
            "rating": "8.8",
            "rating_count": 10000 + index,
            "rank": index,
            "poster_url": f"https://example.com/poster-{index}.jpg",
            "summary": f"Summary for movie {index}.",
            "main_category": "suspense_crime",
            "feature_tags": ["Drama", "Crime"],
        }
        data.update(overrides)
        return Movie.objects.create(**data)

    def test_daily_movie_is_stable_for_the_same_day_and_changes_next_day(self):
        from apps.movies.services.daily_movie import get_daily_movie

        for index in range(1, 4):
            self.make_movie(index)

        today = datetime.date(2026, 5, 18)

        self.assertEqual(get_daily_movie(today), get_daily_movie(today))
        self.assertNotEqual(get_daily_movie(today), get_daily_movie(today + datetime.timedelta(days=1)))

    def test_daily_movie_uses_available_top_ranked_movies_when_less_than_100_exist(self):
        from apps.movies.services.daily_movie import get_daily_movie

        first = self.make_movie(1)

        self.assertEqual(get_daily_movie(datetime.date(2026, 5, 18)), first)

    def test_related_movies_prefer_same_category_and_exclude_current_movie(self):
        from apps.movies.services.daily_movie import get_related_movies

        current = self.make_movie(1, genres=["Drama", "Crime"])
        related = self.make_movie(2, genres=["Drama", "Crime"], rating="9.0")
        self.make_movie(3, main_category="romance_drama", genres=["Romance"])

        results = list(get_related_movies(current, limit=4))

        self.assertIn(related, results)
        self.assertNotIn(current, results)

    def test_homepage_shows_daily_movie_weekly_reputation_chart_and_recommendation_entry(self):
        from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie

        daily = self.make_movie(1)
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="37116446",
            rank=1,
            title="Weekly Movie",
            subtitle="Weekly Alias",
            info_text="Director / Drama / China",
            rating="9.1",
            rating_count=539301,
            poster_url="https://example.com/weekly.webp",
            subject_url="https://movie.douban.com/subject/37116446/",
            fetched_at=timezone.now(),
        )
        DoubanChartMovie.objects.create(
            douban_id="37116612",
            rank=1,
            title="Chart Movie",
            subtitle="Chart Alias",
            info_text="2026-01-01 / Director / Drama",
            rating="9.1",
            rating_count=104955,
            poster_url="https://example.com/chart.webp",
            subject_url="https://movie.douban.com/subject/37116612/",
            fetched_at=timezone.now(),
        )

        response = self.client.get(reverse("blog:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, daily.title)
        self.assertContains(response, "今日电影推荐")
        self.assertContains(response, "近期片讯")
        self.assertContains(response, "一周口碑榜")
        self.assertContains(response, "豆瓣电影排行榜")
        self.assertContains(response, "Weekly Movie")
        self.assertContains(response, "539301人评价")
        self.assertContains(response, "Chart Movie")
        self.assertContains(response, "104955人评价")
        self.assertNotContains(response, "近期预告")
        self.assertNotContains(response, "国内预告")
        self.assertNotContains(response, "国外预告")
        self.assertContains(response, reverse("ratings:category"))

    def test_douban_chart_homepage_links_open_douban_subject_pages(self):
        from apps.blog.models import DoubanChartMovie

        self.make_movie(1)
        DoubanChartMovie.objects.create(
            douban_id="37116612",
            rank=1,
            title="Chart Movie Detail",
            rating="9.1",
            rating_count=104955,
            subject_url="https://movie.douban.com/subject/37116612/",
            fetched_at=timezone.now(),
        )

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, 'href="https://movie.douban.com/subject/37116612/"')
        self.assertNotContains(response, reverse("blog:news_detail", args=[1]))

    def test_news_detail_page_shows_news_information(self):
        from apps.blog.models import UpcomingMovieNews

        news = UpcomingMovieNews.objects.create(
            title="Now Showing Detail",
            original_title="Original Detail",
            event_date=timezone.localdate(),
            event_label="正在热映",
            genre_text="Drama / Mystery",
            poster_url="/static/img/news-posters/now-showing-detail.svg",
            highlight="A full local introduction for this movie.",
            source_name="Source Site",
            source_url="https://example.com/now-showing-detail",
            is_active=True,
            content_type=UpcomingMovieNews.ContentType.NOW_SHOWING,
        )

        response = self.client.get(reverse("blog:news_detail", args=[news.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, news.title)
        self.assertContains(response, news.original_title)
        self.assertContains(response, news.genre_text)
        self.assertContains(response, news.highlight)
        self.assertContains(response, news.source_url)
        self.assertContains(response, news.poster_url)

    def test_homepage_uses_weekly_reputation_module_not_legacy_trailer_sections(self):
        from apps.blog.models import DoubanWeeklyReputationMovie

        daily = self.make_movie(1)
        self.make_movie(2, title="Old Similar Movie", year=1995, rank=101)
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="37116446",
            rank=1,
            title="Weekly Reputation",
            rating="9.1",
            rating_count=539301,
            subject_url="https://movie.douban.com/subject/37116446/",
            fetched_at=timezone.now(),
        )

        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, daily.title)
        self.assertContains(response, "近期片讯")
        self.assertContains(response, "一周口碑榜")
        self.assertContains(response, "Weekly Reputation")
        self.assertNotContains(response, "近期预告")
        self.assertNotContains(response, "国内预告")
        self.assertNotContains(response, "国外预告")
        self.assertNotContains(response, "本周预告")
        self.assertNotContains(response, "近期新片与预告")
        self.assertNotContains(response, "和今日电影相关")
        self.assertNotContains(response, "Old Similar Movie")

    def test_movie_detail_page_shows_movie_information_and_related_movies(self):
        movie = self.make_movie(1)
        related = self.make_movie(2)

        response = self.client.get(reverse("movies:detail", args=[movie.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, movie.title)
        self.assertContains(response, movie.original_title)
        self.assertContains(response, related.title)
        self.assertContains(response, reverse("ratings:category"))

    def test_movie_detail_page_returns_404_for_missing_movie(self):
        response = self.client.get(reverse("movies:detail", args=[999]))

        self.assertEqual(response.status_code, 404)
