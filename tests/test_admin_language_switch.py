from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AdminLanguageSwitchTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="secret12345",
        )
        self.client.force_login(self.user)

    def test_admin_index_shows_language_switcher(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "中文")
        self.assertContains(response, "English")
        self.assertContains(response, reverse("set_language"))

    def test_admin_language_can_switch_to_english(self):
        response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("admin:index")},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Site administration")
        self.assertContains(response, "Blog Management")
        self.assertContains(response, "Movie Library")
        self.assertContains(response, "Recommendation Feedback")

    def test_custom_admin_apps_and_models_use_chinese_labels(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "博客管理")
        self.assertContains(response, "电影管理")
        self.assertContains(response, "评分管理")
        self.assertContains(response, "推荐管理")
        self.assertContains(response, "豆瓣电影排行榜")
        self.assertContains(response, "电影库")
        self.assertContains(response, "评分表")
        self.assertContains(response, "推荐反馈")

    def test_admin_app_order_stays_stable_across_languages(self):
        chinese_response = self.client.get(reverse("admin:index"))
        english_response = self.client.post(
            reverse("set_language"),
            {"language": "en", "next": reverse("admin:index")},
            follow=True,
        )

        chinese_content = chinese_response.content.decode()
        english_content = english_response.content.decode()
        self.assertLess(chinese_content.index("博客管理"), chinese_content.index("认证和授权"))
        self.assertLess(chinese_content.index("推荐管理"), chinese_content.index("认证和授权"))
        self.assertLess(english_content.index("Blog Management"), english_content.index("Authentication and Authorization"))
        self.assertLess(english_content.index("Recommendation Management"), english_content.index("Authentication and Authorization"))
