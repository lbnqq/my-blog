import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.blog.services.poster_fetcher import fetch_douban_poster


class DoubanPosterFallbackTests(SimpleTestCase):
    def test_retries_douban_image_on_alternate_host(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.headers = {"Content-Type": "image/jpeg"}
        response.read.return_value = b"poster-bytes"

        with patch(
            "apps.blog.services.poster_fetcher.urllib.request.urlopen",
            side_effect=[urllib.error.URLError("TLS failed"), response],
        ) as urlopen:
            content, content_type = fetch_douban_poster(
                "https://img1.doubanio.com/view/photo/s_ratio_poster/public/p123.jpg",
                "https://movie.douban.com/subject/123/",
            )

        self.assertEqual(content, b"poster-bytes")
        self.assertEqual(content_type, "image/jpeg")
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(urlopen.call_args_list[1].args[0].full_url, "https://img3.doubanio.com/view/photo/s_ratio_poster/public/p123.jpg")

    def test_non_douban_url_is_not_rewritten(self):
        with patch(
            "apps.blog.services.poster_fetcher.urllib.request.urlopen",
            side_effect=urllib.error.URLError("failed"),
        ) as urlopen:
            with self.assertRaises(urllib.error.URLError):
                fetch_douban_poster(
                    "https://example.com/poster.jpg",
                    "https://example.com/movie/",
                )

        self.assertEqual(urlopen.call_count, 1)
