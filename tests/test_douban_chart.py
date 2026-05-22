import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import DoubanChartMovie
from apps.movies.models import Movie


CHART_HTML = """
<html>
<body>
  <table>
    <tr class="item">
      <td>
        <a class="nbg" href="https://movie.douban.com/subject/37116612/" title="世界的主人">
          <img src="https://img9.doubanio.com/view/photo/s_ratio_poster/public/p123.webp" />
        </a>
      </td>
      <td>
        <div class="pl2">
          <a href="https://movie.douban.com/subject/37116612/">
            世界的主人 / 若问世界谁无伤(港) / 世界之主
          </a>
          <p class="pl">2025-09-07(多伦多电影节) / 2025-10-22(韩国) / 徐粹彬 / 张慧珍 / 韩国 / 尹佳恩 / 119分钟 / 剧情 / 韩语</p>
          <div class="star clearfix">
            <span class="rating_nums">9.1</span>
            <span class="pl">(104955人评价)</span>
          </div>
        </div>
      </td>
    </tr>
    <tr class="item">
      <td>
        <a class="nbg" href="https://movie.douban.com/subject/36995126/" title="爱情抓马">
          <img src="https://img1.doubanio.com/view/photo/s_ratio_poster/public/p456.webp" />
        </a>
      </td>
      <td>
        <div class="pl2">
          <a href="https://movie.douban.com/subject/36995126/">爱情抓马 / 抓马恋人(台)</a>
          <p class="pl">2026-04-01(法国) / 美国 / 克里斯托弗·博格利 / 剧情</p>
          <div class="star clearfix">
            <span class="rating_nums">7.0</span>
            <span class="pl">(28746人评价)</span>
          </div>
        </div>
      </td>
    </tr>
  </table>
</body>
</html>
"""


class DoubanChartParserTests(TestCase):
    def test_parse_chart_extracts_ranked_movie_information(self):
        from apps.blog.services.douban_chart import parse_douban_chart

        entries = parse_douban_chart(CHART_HTML)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0].douban_id, "37116612")
        self.assertEqual(entries[0].rank, 1)
        self.assertEqual(entries[0].title, "世界的主人")
        self.assertEqual(entries[0].subtitle, "若问世界谁无伤(港) / 世界之主")
        self.assertIn("2025-09-07", entries[0].info_text)
        self.assertEqual(entries[0].rating, Decimal("9.1"))
        self.assertEqual(entries[0].rating_count, 104955)
        self.assertEqual(entries[0].poster_url, "https://img9.doubanio.com/view/photo/s_ratio_poster/public/p123.webp")
        self.assertEqual(entries[0].subject_url, "https://movie.douban.com/subject/37116612/")


class DoubanChartSyncTests(TestCase):
    def test_sync_chart_creates_updates_and_deactivates_missing_movies(self):
        from apps.blog.services.douban_chart import sync_douban_chart

        stale = DoubanChartMovie.objects.create(
            douban_id="old",
            rank=1,
            title="旧榜单电影",
            rating=Decimal("8.0"),
            rating_count=1000,
            subject_url="https://movie.douban.com/subject/00000000/",
            fetched_at=timezone.now() - datetime.timedelta(days=10),
        )

        result = sync_douban_chart(fetch_html=lambda: CHART_HTML, force=True)

        self.assertEqual(result.status, "updated")
        self.assertEqual(result.updated_count, 2)
        stale.refresh_from_db()
        self.assertFalse(stale.is_active)
        first = DoubanChartMovie.objects.get(douban_id="37116612")
        self.assertTrue(first.is_active)
        self.assertEqual(first.rank, 1)
        self.assertEqual(first.rating, Decimal("9.1"))

    def test_sync_chart_skips_when_recent_data_exists_without_force(self):
        from apps.blog.services.douban_chart import sync_douban_chart

        recent = timezone.now() - datetime.timedelta(days=1)
        DoubanChartMovie.objects.create(
            douban_id="37116612",
            rank=1,
            title="世界的主人",
            rating=Decimal("9.1"),
            rating_count=104955,
            subject_url="https://movie.douban.com/subject/37116612/",
            fetched_at=recent,
        )

        called = False

        def fetch_html():
            nonlocal called
            called = True
            return CHART_HTML

        result = sync_douban_chart(fetch_html=fetch_html)

        self.assertEqual(result.status, "skipped")
        self.assertFalse(called)

    def test_sync_chart_keeps_existing_data_when_fetch_returns_no_entries(self):
        from apps.blog.services.douban_chart import sync_douban_chart

        existing = DoubanChartMovie.objects.create(
            douban_id="37116612",
            rank=1,
            title="世界的主人",
            rating=Decimal("9.1"),
            rating_count=104955,
            subject_url="https://movie.douban.com/subject/37116612/",
            fetched_at=timezone.now() - datetime.timedelta(days=10),
        )

        result = sync_douban_chart(fetch_html=lambda: "<html></html>", force=True)

        self.assertEqual(result.status, "failed")
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)


class DoubanChartCommandTests(TestCase):
    def test_management_command_forwards_force_option(self):
        with patch("apps.blog.management.commands.sync_douban_chart.sync_douban_chart") as sync:
            sync.return_value.status = "updated"
            sync.return_value.updated_count = 2
            sync.return_value.message = "Updated 2 Douban chart movies."

            call_command("sync_douban_chart", "--force")

        sync.assert_called_once_with(force=True)


class DoubanChartHomepageTests(TestCase):
    def make_daily_movie(self):
        return Movie.objects.create(
            douban_id="daily-1",
            title="每日电影",
            year=2001,
            directors=["导演"],
            actors=["演员"],
            genres=["剧情"],
            countries=["中国"],
            rating="8.8",
            rating_count=1000,
            rank=1,
            poster_url="",
            summary="每日电影简介。",
            main_category="romance_drama",
            feature_tags=["剧情"],
        )

    def test_homepage_shows_douban_chart_movies_with_external_detail_links(self):
        self.make_daily_movie()
        for index in range(1, 8):
            DoubanChartMovie.objects.create(
                douban_id=f"chart-{index}",
                rank=index,
                title=f"榜单电影 {index}",
                subtitle=f"别名 {index}",
                info_text="2026-01-01 / 导演 / 剧情",
                rating=Decimal("8.5"),
                rating_count=10000 + index,
                poster_url=f"https://example.com/chart-{index}.webp",
                subject_url=f"https://movie.douban.com/subject/{index}/",
                fetched_at=timezone.now(),
            )

        response = self.client.get(reverse("blog:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "豆瓣电影排行榜")
        self.assertContains(response, "榜单电影 1")
        self.assertContains(response, "10001人评价")
        self.assertContains(response, 'href="https://movie.douban.com/subject/1/"')
        self.assertContains(response, reverse("blog:douban_chart_poster", args=["chart-1"]))
        self.assertNotContains(response, "榜单电影 7")
        self.assertNotContains(response, reverse("blog:news_detail", args=[1]))

    def test_douban_chart_poster_proxy_streams_remote_poster(self):
        DoubanChartMovie.objects.create(
            douban_id="37116612",
            rank=1,
            title="世界的主人",
            rating=Decimal("9.1"),
            rating_count=104955,
            poster_url="https://img9.doubanio.com/view/photo/s_ratio_poster/public/p123.webp",
            subject_url="https://movie.douban.com/subject/37116612/",
            fetched_at=timezone.now(),
        )

        with patch("apps.blog.views.fetch_douban_chart_poster", return_value=(b"poster-bytes", "image/webp")):
            response = self.client.get(reverse("blog:douban_chart_poster", args=["37116612"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response.content, b"poster-bytes")
