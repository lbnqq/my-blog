import json
import base64
import hashlib
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie
from apps.movies.models import Movie
from apps.recommendations.models import SyncRun


class AgentTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="agent-user", password="secret12345"
        )
        self.movie = Movie.objects.create(
            douban_id="1291546",
            title="霸王别姬",
            original_title="",
            year=1993,
            directors=["陈凯歌"],
            actors=["张国荣", "张丰毅"],
            genres=["剧情", "爱情"],
            countries=["中国大陆"],
            rating=Decimal("9.6"),
            rating_count=2100000,
            rank=1,
            poster_url="",
            summary="风华绝代的时代悲歌。",
            main_category="romance_drama",
            feature_tags=["剧情", "经典"],
        )
        DoubanChartMovie.objects.create(
            douban_id="chart-1",
            rank=1,
            title="Chart Agent Movie",
            rating="8.8",
            rating_count=12345,
            subject_url="https://movie.douban.com/subject/chart-1/",
            fetched_at=timezone.now(),
        )
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="weekly-1",
            rank=1,
            title="Weekly Agent Movie",
            rating="9.1",
            rating_count=54321,
            subject_url="https://movie.douban.com/subject/weekly-1/",
            fetched_at=timezone.now(),
        )

    def post_chat(self, message):
        return self.client.post(
            reverse("agent:chat"),
            data=json.dumps({"message": message}),
            content_type="application/json",
        )

    @override_settings(ZHIPU_API_KEY="", SITE_PUBLIC_URL="https://movie.example.com")
    def test_guest_can_ask_blog_intro_charts_search_and_recommendation_entry(self):
        intro = self.post_chat("这个博客是干什么的？")
        self.assertEqual(intro.status_code, 200)
        self.assertIn("个性化推荐", intro.json()["reply"])

        charts = self.post_chat("一周口碑榜和排行榜有哪些？")
        self.assertContains(charts, "Weekly Agent Movie")
        self.assertContains(charts, "Chart Agent Movie")

        search = self.post_chat("搜索电影 霸王别姬")
        search_payload = search.json()
        self.assertIn("霸王别姬", search_payload["reply"])
        self.assertIn(reverse("movies:detail", args=[self.movie.pk]), json.dumps(search_payload, ensure_ascii=False))

        recommendation = self.post_chat("给我推荐电影")
        payload = recommendation.json()
        self.assertIn("进入推荐页面", payload["reply"])
        self.assertIn(reverse("ratings:category"), json.dumps(payload, ensure_ascii=False))

    @override_settings(ZHIPU_API_KEY="")
    def test_guest_sync_request_requires_login_and_does_not_create_action(self):
        response = self.post_chat("帮我更新口碑榜")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("登录", payload["reply"])
        self.assertFalse(payload["requires_confirmation"])
        self.assertEqual(SyncRun.objects.count(), 0)

    @override_settings(ZHIPU_API_KEY="")
    def test_logged_in_sync_request_creates_pending_confirmation_only(self):
        self.client.force_login(self.user)

        response = self.post_chat("帮我更新排行榜")

        payload = response.json()
        self.assertTrue(payload["requires_confirmation"])
        self.assertEqual(payload["actions"][0]["type"], "confirm_sync")
        self.assertEqual(SyncRun.objects.count(), 0)

    @override_settings(ZHIPU_API_KEY="")
    def test_confirm_sync_executes_action_and_creates_sync_log(self):
        self.client.force_login(self.user)
        pending = self.post_chat("更新口碑榜").json()
        action_id = pending["actions"][0]["action_id"]

        with patch("apps.agent.services.sync_douban_weekly_reputation") as sync:
            sync.return_value.status = "updated"
            sync.return_value.updated_count = 6
            sync.return_value.message = "updated 6 weekly movies"
            response = self.client.post(
                reverse("agent:confirm_action"),
                data=json.dumps({"action_id": action_id}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        run = SyncRun.objects.get()
        self.assertEqual(run.source, SyncRun.Source.WEEKLY_REPUTATION)
        self.assertEqual(run.triggered_by, self.user)

    @override_settings(ZHIPU_API_KEY="")
    def test_generic_sync_request_executes_all_sources_after_confirmation(self):
        self.client.force_login(self.user)
        pending = self.post_chat("更新榜单").json()
        action_id = pending["actions"][0]["action_id"]

        with patch("apps.agent.services.sync_douban_chart") as chart_sync, patch(
            "apps.agent.services.sync_douban_weekly_reputation"
        ) as weekly_sync:
            chart_sync.return_value.status = "updated"
            chart_sync.return_value.updated_count = 2
            chart_sync.return_value.message = "updated chart"
            weekly_sync.return_value.status = "updated"
            weekly_sync.return_value.updated_count = 6
            weekly_sync.return_value.message = "updated weekly"
            response = self.client.post(
                reverse("agent:confirm_action"),
                data=json.dumps({"action_id": action_id}),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SyncRun.objects.count(), 2)
        self.assertEqual(
            set(SyncRun.objects.values_list("source", flat=True)),
            {SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION},
        )

    @override_settings(ZHIPU_API_KEY="")
    def test_sync_failure_with_retained_cache_returns_friendly_warning(self):
        self.client.force_login(self.user)
        pending = self.post_chat("更新榜单").json()
        action_id = pending["actions"][0]["action_id"]

        with patch("apps.agent.services.sync_douban_chart") as chart_sync, patch(
            "apps.agent.services.sync_douban_weekly_reputation"
        ) as weekly_sync:
            chart_sync.return_value.status = "failed"
            chart_sync.return_value.updated_count = 0
            chart_sync.return_value.message = "豆瓣同步失败，现有 10 条榜单缓存已过期但仍保留。网络原因：ssl eof"
            weekly_sync.return_value.status = "failed"
            weekly_sync.return_value.updated_count = 0
            weekly_sync.return_value.message = "豆瓣同步失败，现有 6 条口碑榜缓存已过期但仍保留。网络原因：curl tls"
            response = self.client.post(
                reverse("agent:confirm_action"),
                data=json.dumps({"action_id": action_id}),
                content_type="application/json",
            )

        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "degraded")
        self.assertIn("继续使用现有缓存", payload["reply"])
        self.assertIn("稍后再试", payload["reply"])
        self.assertNotIn("ssl eof", payload["reply"])
        self.assertNotIn("curl tls", payload["reply"])

    @override_settings(ZHIPU_API_KEY="")
    def test_sync_hard_failure_hides_low_level_network_details(self):
        self.client.force_login(self.user)
        pending = self.post_chat("更新排行榜").json()
        action_id = pending["actions"][0]["action_id"]

        with patch("apps.agent.services.sync_douban_chart") as chart_sync:
            chart_sync.return_value.status = "failed"
            chart_sync.return_value.updated_count = 0
            chart_sync.return_value.message = "Failed to fetch Douban chart: 网络原因：ssl secret detail"
            response = self.client.post(
                reverse("agent:confirm_action"),
                data=json.dumps({"action_id": action_id}),
                content_type="application/json",
            )

        payload = response.json()
        self.assertEqual(payload["status"], "failed")
        self.assertIn("同步已执行", payload["reply"])
        self.assertNotIn("ssl secret detail", payload["reply"])

    @override_settings(ZHIPU_API_KEY="")
    def test_confirm_sync_rejects_recent_same_source_run(self):
        self.client.force_login(self.user)
        SyncRun.objects.create(
            source=SyncRun.Source.DOUBAN_CHART,
            status=SyncRun.Status.SUCCESS,
            updated_count=1,
            message="recent",
            triggered_by=self.user,
            finished_at=timezone.now() - timedelta(minutes=1),
        )
        pending = self.post_chat("更新排行榜").json()
        action_id = pending["actions"][0]["action_id"]

        response = self.client.post(
            reverse("agent:confirm_action"),
            data=json.dumps({"action_id": action_id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 429)
        self.assertIn("10 分钟", response.json()["reply"])

    def test_agent_chat_requires_post_and_csrf(self):
        self.assertEqual(self.client.get(reverse("agent:chat")).status_code, 405)

        csrf_client = Client(enforce_csrf_checks=True)
        response = csrf_client.post(
            reverse("agent:chat"),
            data=json.dumps({"message": "你好"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(ZHIPU_API_KEY="")
    def test_invalid_action_id_returns_error_without_leaking_secrets(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("agent:confirm_action"),
            data=json.dumps({"action_id": "missing"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("ZHIPU_API_KEY", response.content.decode())

    def test_homepage_renders_floating_agent_entry(self):
        response = self.client.get(reverse("blog:home"))

        self.assertContains(response, "movie-agent")
        self.assertContains(response, reverse("agent:chat"))


class FeishuAgentTests(TestCase):
    def setUp(self):
        Movie.objects.create(
            douban_id="1291546",
            title="霸王别姬",
            original_title="",
            year=1993,
            directors=["陈凯歌"],
            actors=["张国荣", "张丰毅"],
            genres=["剧情", "爱情"],
            countries=["中国大陆"],
            rating=Decimal("9.6"),
            rating_count=2100000,
            rank=1,
            poster_url="",
            summary="风华绝代的时代悲歌。",
            main_category="romance_drama",
            feature_tags=["剧情", "经典"],
        )
        DoubanChartMovie.objects.create(
            douban_id="chart-1",
            rank=1,
            title="Chart Agent Movie",
            rating="8.8",
            rating_count=12345,
            subject_url="https://movie.douban.com/subject/chart-1/",
            fetched_at=timezone.now(),
        )
        DoubanWeeklyReputationMovie.objects.create(
            douban_id="weekly-1",
            rank=1,
            title="Weekly Agent Movie",
            rating="9.1",
            rating_count=54321,
            subject_url="https://movie.douban.com/subject/weekly-1/",
            fetched_at=timezone.now(),
        )

    def post_event(self, payload):
        return self.client.post(
            reverse("agent:feishu_events"),
            data=json.dumps(payload),
            content_type="application/json",
        )

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token")
    def test_feishu_url_verification_challenge_returns_plain_challenge(self):
        response = self.post_event(
            {
                "type": "url_verification",
                "token": "verify-token",
                "challenge": "challenge-value",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"challenge": "challenge-value"})

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token")
    def test_feishu_url_verification_rejects_invalid_token(self):
        response = self.post_event(
            {
                "type": "url_verification",
                "token": "wrong-token",
                "challenge": "challenge-value",
            }
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token")
    def test_feishu_rejects_encrypted_payload_when_decryption_is_unavailable(self):
        response = self.post_event({"encrypt": "not-valid-ciphertext"})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "invalid_encryption")

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", FEISHU_ENCRYPT_KEY="encrypt-key")
    def test_feishu_decrypts_url_verification_payload(self):
        encrypted = encrypt_feishu_payload(
            {
                "type": "url_verification",
                "token": "verify-token",
                "challenge": "encrypted-challenge",
            },
            "encrypt-key",
        )

        response = self.post_event({"encrypt": encrypted})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"challenge": "encrypted-challenge"})

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", FEISHU_ENCRYPT_KEY="encrypt-key")
    def test_feishu_rejects_invalid_lark_signature(self):
        response = self.client.post(
            reverse("agent:feishu_events"),
            data=json.dumps({"type": "url_verification", "token": "verify-token", "challenge": "value"}),
            content_type="application/json",
            HTTP_X_LARK_SIGNATURE="bad-signature",
            HTTP_X_LARK_REQUEST_TIMESTAMP="123",
            HTTP_X_LARK_REQUEST_NONCE="nonce",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "invalid_signature")

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", SITE_PUBLIC_URL="https://movie.example.com")
    @patch("apps.agent.feishu.reply_to_feishu_message")
    def test_feishu_blog_intro_message_replies_with_agent_answer(self, reply):
        response = self.post_event(self.message_payload("这个博客有什么内容"))

        self.assertEqual(response.status_code, 200)
        reply.assert_called_once()
        self.assertIn("个性化推荐", reply.call_args.args[1])

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", SITE_PUBLIC_URL="https://movie.example.com")
    @patch("apps.agent.feishu.reply_to_feishu_message")
    def test_feishu_charts_message_replies_with_homepage_data(self, reply):
        response = self.post_event(self.message_payload("一周口碑榜和排行榜有哪些"))

        self.assertEqual(response.status_code, 200)
        text = reply.call_args.args[1]
        self.assertIn("Weekly Agent Movie", text)
        self.assertIn("Chart Agent Movie", text)

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", SITE_PUBLIC_URL="https://movie.example.com")
    @patch("apps.agent.feishu.reply_to_feishu_message")
    def test_feishu_search_message_replies_with_movie_links(self, reply):
        response = self.post_event(self.message_payload("搜索电影 霸王别姬"))

        self.assertEqual(response.status_code, 200)
        text = reply.call_args.args[1]
        self.assertIn("霸王别姬", text)
        self.assertIn("https://movie.example.com/movies/", text)

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token", SITE_PUBLIC_URL="https://movie.example.com")
    @patch("apps.agent.feishu.reply_to_feishu_message")
    def test_feishu_recommendation_message_returns_site_entry(self, reply):
        response = self.post_event(self.message_payload("给我推荐电影"))

        self.assertEqual(response.status_code, 200)
        text = reply.call_args.args[1]
        self.assertIn("进入推荐页面", text)
        self.assertIn("https://movie.example.com/recommend/", text)

    @override_settings(FEISHU_VERIFICATION_TOKEN="verify-token")
    @patch("apps.agent.feishu.reply_to_feishu_message")
    def test_feishu_sync_message_never_creates_sync_run(self, reply):
        response = self.post_event(self.message_payload("同步榜单"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SyncRun.objects.count(), 0)
        self.assertIn("飞书里不能直接执行", reply.call_args.args[1])

    def message_payload(self, text):
        return {
            "schema": "2.0",
            "header": {
                "event_type": "im.message.receive_v1",
                "token": "verify-token",
            },
            "event": {
                "message": {
                    "message_id": "om_test_message",
                    "message_type": "text",
                    "content": json.dumps({"text": text}, ensure_ascii=False),
                }
            },
        }


def encrypt_feishu_payload(payload, encrypt_key):
    key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
    iv = b"0123456789abcdef"
    padder = PKCS7(128).padder()
    padded = padder.update(json.dumps(payload, ensure_ascii=False).encode("utf-8")) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode("utf-8")
