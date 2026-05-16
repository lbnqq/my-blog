from django.test import SimpleTestCase

from apps.recommendations.services.reason_generator import generate_reason


class ReasonGeneratorTests(SimpleTestCase):
    def test_generate_reason_mentions_source_movie_and_tags(self):
        reason = generate_reason("致命魔术", ["盗梦空间"], ["悬疑", "反转"], "悬疑犯罪", 8.9)
        self.assertIn("盗梦空间", reason)
        self.assertIn("悬疑", reason)
        self.assertIn("豆瓣评分较高", reason)
