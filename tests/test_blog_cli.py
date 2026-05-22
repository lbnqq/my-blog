from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.db.utils import ProgrammingError
from django.test import TestCase
from django.utils import timezone

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie
from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.ratings.models import RatingForm, RatingFormMovie, UserSession


class BlogCliTests(TestCase):
    def create_movie(self, index, **overrides):
        defaults = {
            "douban_id": f"movie-{index}",
            "title": f"Movie {index}",
            "original_title": "",
            "year": 2000 + index,
            "directors": [f"Director {index % 3}"],
            "actors": [f"Actor {index}"],
            "genres": ["剧情", "爱情"],
            "countries": ["中国"],
            "rating": Decimal("8.5"),
            "rating_count": 1000 + index,
            "rank": index,
            "poster_url": "",
            "summary": f"Summary {index}",
            "main_category": "romance_drama",
            "feature_tags": ["剧情", "高分"],
        }
        defaults.update(overrides)
        return Movie.objects.create(**defaults)

    def test_home_prints_homepage_sections(self):
        self.create_movie(1, title="Daily Movie")
        DoubanChartMovie.objects.create(
            douban_id="chart-1",
            rank=1,
            title="Chart Movie",
            subtitle="Chart Alias",
            info_text="Chart info",
            rating=Decimal("9.1"),
            rating_count=12345,
            poster_url="https://example.com/chart.jpg",
            subject_url="https://movie.douban.com/subject/chart-1/",
            fetched_at=timezone.now(),
            is_active=True,
        )
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="weekly-1",
            rank=1,
            title="Weekly Movie",
            subtitle="Weekly Alias",
            info_text="Weekly info",
            rating=Decimal("8.9"),
            rating_count=54321,
            poster_url="https://example.com/weekly.jpg",
            subject_url="https://movie.douban.com/subject/weekly-1/",
            fetched_at=timezone.now(),
            is_active=True,
        )

        stdout = StringIO()
        call_command("blog", "home", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("每日一片", output)
        self.assertIn("Daily Movie", output)
        self.assertIn("豆瓣电影排行榜", output)
        self.assertIn("Chart Movie", output)
        self.assertIn("豆瓣一周口碑榜", output)
        self.assertIn("Weekly Movie", output)

    @patch("apps.blog.management.commands.blog.get_homepage_weekly_reputation")
    @patch("apps.blog.management.commands.blog.get_homepage_douban_chart")
    def test_home_reports_missing_chart_tables_without_traceback(self, chart_rows, weekly_rows):
        self.create_movie(1, title="Daily Movie")
        chart_rows.side_effect = ProgrammingError('relation "blog_doubanchartmovie" does not exist')
        weekly_rows.side_effect = ProgrammingError('relation "blog_doubanweeklyreputationmovie" does not exist')

        stdout = StringIO()
        call_command("blog", "home", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("每日一片", output)
        self.assertIn("Daily Movie", output)
        self.assertIn("豆瓣电影排行榜", output)
        self.assertIn("数据表不存在，请先运行数据库迁移", output)
        self.assertIn("豆瓣一周口碑榜", output)

    @patch("apps.blog.management.commands.blog.sync_douban_weekly_reputation")
    @patch("apps.blog.management.commands.blog.sync_douban_chart")
    def test_sync_defaults_to_both_charts(self, sync_chart, sync_weekly):
        sync_chart.return_value.status = "updated"
        sync_chart.return_value.message = "chart synced"
        sync_weekly.return_value.status = "updated"
        sync_weekly.return_value.message = "weekly synced"

        stdout = StringIO()
        call_command("blog", "sync", stdout=stdout)

        sync_chart.assert_called_once_with(force=False)
        sync_weekly.assert_called_once_with(force=False)
        self.assertIn("chart synced", stdout.getvalue())
        self.assertIn("weekly synced", stdout.getvalue())

    def test_movies_search_and_show(self):
        movie = self.create_movie(1, title="霸王别姬", douban_id="1291546", year=1993)

        search_stdout = StringIO()
        call_command("blog", "movies", "search", "霸王", stdout=search_stdout)
        self.assertIn("霸王别姬", search_stdout.getvalue())
        self.assertIn("1291546", search_stdout.getvalue())

        show_stdout = StringIO()
        call_command("blog", "movies", "show", str(movie.pk), stdout=show_stdout)
        self.assertIn("霸王别姬", show_stdout.getvalue())
        self.assertIn("Summary 1", show_stdout.getvalue())

    def test_recommend_interactive_flow_creates_results(self):
        form = RatingForm.objects.create(
            category="romance_drama",
            title="爱情剧情评分表",
            is_active=True,
        )
        for index in range(1, 11):
            movie = self.create_movie(index)
            RatingFormMovie.objects.create(form=form, movie=movie, sort_order=index)
        for index in range(11, 16):
            self.create_movie(index)

        answers = iter(["5", "5", "4", "4", "3", "3", "2", "1", "", ""])
        stdout = StringIO()
        with patch("builtins.input", side_effect=lambda _prompt: next(answers)):
            call_command("blog", "recommend", "--category", "romance_drama", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("推荐结果", output)
        self.assertEqual(UserSession.objects.count(), 1)
        session = UserSession.objects.get()
        self.assertGreaterEqual(session.ratings.count(), 8)
        self.assertGreater(session.recommendation_results.count(), 0)

    def test_doctor_reports_core_status(self):
        self.create_movie(1)
        for category in CATEGORY_LABELS:
            RatingForm.objects.create(category=category, title=f"{category} 评分表", is_active=True)
        DoubanChartMovie.objects.create(
            douban_id="chart-1",
            rank=1,
            title="Chart Movie",
            subject_url="https://movie.douban.com/subject/chart-1/",
            fetched_at=timezone.now(),
            is_active=True,
        )
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="weekly-1",
            rank=1,
            title="Weekly Movie",
            subject_url="https://movie.douban.com/subject/weekly-1/",
            fetched_at=timezone.now(),
            is_active=True,
        )

        stdout = StringIO()
        call_command("blog", "doctor", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("数据库连接: OK", output)
        self.assertIn("电影数据: OK", output)
        self.assertIn("豆瓣电影排行榜: OK", output)
        self.assertIn("豆瓣一周口碑榜: OK", output)
        self.assertIn("评分表: OK", output)

    @patch("apps.blog.management.commands.blog.DoubanChartMovie.objects")
    def test_doctor_reports_missing_tables_without_traceback(self, chart_objects):
        self.create_movie(1)
        chart_objects.filter.side_effect = ProgrammingError('relation "blog_doubanchartmovie" does not exist')

        stdout = StringIO()
        call_command("blog", "doctor", stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("数据库连接: OK", output)
        self.assertIn("豆瓣电影排行榜: WARN", output)
        self.assertIn("数据表不存在，请先运行迁移", output)
