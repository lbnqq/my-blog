import datetime
from decimal import Decimal
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import DoubanWeeklyReputationMovie
from apps.movies.models import Movie


CHART_HTML = """
<html>
<body>
  <div class="billboard">
    <h2>一周口碑榜</h2>
    <table>
      <tr>
        <td class="order">1</td>
        <td class="title"><a href="https://movie.douban.com/subject/37116446/">给阿嬷的情书</a></td>
        <td><span class="up">1</span></td>
      </tr>
      <tr>
        <td class="order">2</td>
        <td class="title"><a href="https://movie.douban.com/subject/37116612/">世界的主人</a></td>
        <td><span class="down">1</span></td>
      </tr>
      <tr>
        <td class="order">3</td>
        <td class="title"><a href="https://movie.douban.com/subject/37069578/">万事顺利</a></td>
        <td><span class="up">8</span></td>
      </tr>
      <tr>
        <td class="order">4</td>
        <td class="title"><a href="https://movie.douban.com/subject/36631864/">奇幻变身大冒险</a></td>
        <td><span class="up">2</span></td>
      </tr>
      <tr>
        <td class="order">5</td>
        <td class="title"><a href="https://movie.douban.com/subject/35182657/">母鸡</a></td>
        <td><span class="up">4</span></td>
      </tr>
      <tr>
        <td class="order">6</td>
        <td class="title"><a href="https://movie.douban.com/subject/34930810/">平场之月</a></td>
        <td><span class="up">5</span></td>
      </tr>
      <tr>
        <td class="order">7</td>
        <td class="title"><a href="https://movie.douban.com/subject/36995126/">爱情抓马</a></td>
      </tr>
    </table>
  </div>
</body>
</html>
"""


SUBJECT_HTML = """
<html>
<body>
  <h1><span property="v:itemreviewed">给阿嬷的情书 Dear You (2026)</span></h1>
  <div id="mainpic">
    <img src="https://img1.doubanio.com/view/photo/s_ratio_poster/public/p789.webp" />
  </div>
  <div id="info">
    <span><span class="pl">导演</span>: 蓝鸿春</span><br/>
    <span><span class="pl">主演</span>: 李思萍 / 王彦桦 / 吴心卿</span><br/>
    <span class="pl">类型:</span> 剧情 / 家庭<br/>
    <span class="pl">制片国家/地区:</span> 中国大陆<br/>
    <span class="pl">上映日期:</span> 2026-04-30(中国大陆)<br/>
    <span class="pl">片长:</span> 118分钟<br/>
  </div>
  <strong class="ll rating_num" property="v:average">9.1</strong>
  <span property="v:votes">539301</span>
</body>
</html>
"""

SUBJECT_JSON = """
{
  "title": "给阿嬷的情书",
  "year": "2026",
  "aka": ["Dear You"],
  "card_subtitle": "2026 / 中国大陆 / 剧情 家庭 / 蓝鸿春 / 李思潼 王彦桐",
  "rating": {"value": 9.1, "count": 539301},
  "cover": {
    "image": {
      "normal": {
        "url": "https://img1.doubanio.com/view/photo/m/public/p2931851430.jpg"
      }
    }
  }
}
"""


class DoubanWeeklyReputationParserTests(TestCase):
    def test_parse_weekly_reputation_chart_extracts_first_six_subjects(self):
        from apps.blog.services.douban_weekly_reputation import parse_weekly_reputation_chart

        entries = parse_weekly_reputation_chart(CHART_HTML, limit=6)

        self.assertEqual(len(entries), 6)
        self.assertEqual(entries[0].douban_id, "37116446")
        self.assertEqual(entries[0].rank, 1)
        self.assertEqual(entries[0].title, "给阿嬷的情书")
        self.assertEqual(entries[0].subject_url, "https://movie.douban.com/subject/37116446/")
        self.assertEqual(entries[-1].rank, 6)
        self.assertEqual(entries[-1].title, "平场之月")

    def test_parse_subject_detail_enriches_weekly_reputation_entry(self):
        from apps.blog.services.douban_weekly_reputation import parse_subject_detail

        detail = parse_subject_detail(SUBJECT_HTML)

        self.assertEqual(detail.title, "给阿嬷的情书")
        self.assertEqual(detail.subtitle, "Dear You (2026)")
        self.assertIn("蓝鸿春", detail.info_text)
        self.assertIn("剧情 / 家庭", detail.info_text)
        self.assertEqual(detail.rating, Decimal("9.1"))
        self.assertEqual(detail.rating_count, 539301)
        self.assertEqual(detail.poster_url, "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p789.webp")

    def test_parse_subject_detail_accepts_mobile_json_detail(self):
        from apps.blog.services.douban_weekly_reputation import parse_subject_detail

        detail = parse_subject_detail(SUBJECT_JSON)

        self.assertEqual(detail.title, "给阿嬷的情书")
        self.assertEqual(detail.subtitle, "Dear You (2026)")
        self.assertIn("中国大陆", detail.info_text)
        self.assertEqual(detail.rating, Decimal("9.1"))
        self.assertEqual(detail.rating_count, 539301)
        self.assertEqual(detail.poster_url, "https://img1.doubanio.com/view/photo/m/public/p2931851430.jpg")


class DoubanWeeklyReputationSyncTests(TestCase):
    def fetch_subject(self, url):
        return SUBJECT_HTML

    def test_sync_weekly_reputation_creates_updates_and_deactivates_missing_movies(self):
        from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation

        stale = DoubanWeeklyReputationMovie.objects.create(
            douban_id="old",
            rank=1,
            title="旧口碑电影",
            rating=Decimal("8.0"),
            rating_count=1000,
            subject_url="https://movie.douban.com/subject/00000000/",
            fetched_at=timezone.now() - datetime.timedelta(days=10),
        )

        result = sync_douban_weekly_reputation(
            fetch_chart_html=lambda: CHART_HTML,
            fetch_subject_html=self.fetch_subject,
            force=True,
        )

        self.assertEqual(result.status, "updated")
        self.assertEqual(result.updated_count, 6)
        stale.refresh_from_db()
        self.assertFalse(stale.is_active)
        first = DoubanWeeklyReputationMovie.objects.get(douban_id="37116446")
        self.assertEqual(first.title, "给阿嬷的情书")
        self.assertEqual(first.rating, Decimal("9.1"))
        self.assertTrue(first.is_active)

    def test_sync_weekly_reputation_skips_when_recent_data_exists_without_force(self):
        from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation

        DoubanWeeklyReputationMovie.objects.create(
            douban_id="37116446",
            rank=1,
            title="给阿嬷的情书",
            rating=Decimal("9.1"),
            rating_count=539301,
            subject_url="https://movie.douban.com/subject/37116446/",
            fetched_at=timezone.now() - datetime.timedelta(days=2),
        )

        called = False

        def fetch_chart_html():
            nonlocal called
            called = True
            return CHART_HTML

        result = sync_douban_weekly_reputation(fetch_chart_html=fetch_chart_html)

        self.assertEqual(result.status, "skipped")
        self.assertFalse(called)

    def test_sync_weekly_reputation_keeps_existing_data_when_no_entries_parse(self):
        from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation

        existing = DoubanWeeklyReputationMovie.objects.create(
            douban_id="37116446",
            rank=1,
            title="给阿嬷的情书",
            rating=Decimal("9.1"),
            rating_count=539301,
            subject_url="https://movie.douban.com/subject/37116446/",
            fetched_at=timezone.now() - datetime.timedelta(days=10),
        )

        result = sync_douban_weekly_reputation(fetch_chart_html=lambda: "<html></html>", force=True)

        self.assertEqual(result.status, "failed")
        existing.refresh_from_db()
        self.assertTrue(existing.is_active)


class DoubanWeeklyReputationCommandTests(TestCase):
    def test_management_command_forwards_force_option(self):
        with patch(
            "apps.blog.management.commands.sync_douban_weekly_reputation.sync_douban_weekly_reputation"
        ) as sync:
            sync.return_value.status = "updated"
            sync.return_value.updated_count = 6
            sync.return_value.message = "Updated 6 Douban weekly reputation movies."

            call_command("sync_douban_weekly_reputation", "--force")

        sync.assert_called_once_with(force=True)


class DoubanWeeklyReputationHomepageTests(TestCase):
    def make_daily_movie(self):
        return Movie.objects.create(
            douban_id="daily-weekly-1",
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

    def test_homepage_replaces_upcoming_news_with_weekly_reputation_cards(self):
        self.make_daily_movie()
        for index in range(1, 8):
            DoubanWeeklyReputationMovie.objects.create(
                douban_id=f"weekly-{index}",
                rank=index,
                title=f"口碑电影 {index}",
                subtitle=f"别名 {index}",
                info_text="导演 / 类型 / 地区",
                rating=Decimal("8.5"),
                rating_count=20000 + index,
                poster_url=f"https://example.com/weekly-{index}.webp",
                subject_url=f"https://movie.douban.com/subject/{index}/",
                fetched_at=timezone.now(),
            )

        response = self.client.get(reverse("blog:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "一周口碑榜")
        self.assertContains(response, "口碑电影 1")
        self.assertContains(response, "20001人评价")
        self.assertContains(response, reverse("blog:douban_weekly_reputation_poster", args=["weekly-1"]))
        self.assertContains(response, 'href="https://movie.douban.com/subject/1/"')
        self.assertNotContains(response, "近期预告")
        self.assertNotContains(response, "国内预告")
        self.assertNotContains(response, "国外预告")
        self.assertNotContains(response, "口碑电影 7")

    def test_weekly_reputation_poster_proxy_streams_remote_poster(self):
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="37116446",
            rank=1,
            title="给阿嬷的情书",
            rating=Decimal("9.1"),
            rating_count=539301,
            poster_url="https://img1.doubanio.com/view/photo/s_ratio_poster/public/p789.webp",
            subject_url="https://movie.douban.com/subject/37116446/",
            fetched_at=timezone.now(),
        )

        with patch("apps.blog.views.fetch_douban_weekly_reputation_poster", return_value=(b"poster", "image/webp")):
            response = self.client.get(reverse("blog:douban_weekly_reputation_poster", args=["37116446"]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response.content, b"poster")
