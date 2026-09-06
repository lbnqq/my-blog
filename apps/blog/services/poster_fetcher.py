import urllib.error
import urllib.parse
import urllib.request


DOUBAN_IMAGE_HOSTS = ("img3.doubanio.com", "img9.doubanio.com")


def poster_candidates(poster_url):
    yield poster_url
    parsed = urllib.parse.urlsplit(poster_url)
    if not parsed.hostname or not parsed.hostname.endswith(".doubanio.com"):
        return

    for host in DOUBAN_IMAGE_HOSTS:
        if host == parsed.hostname:
            continue
        yield urllib.parse.urlunsplit(
            (parsed.scheme, host, parsed.path, parsed.query, parsed.fragment)
        )


def fetch_douban_poster(poster_url, subject_url):
    last_error = None
    for candidate in poster_candidates(poster_url):
        request = urllib.request.Request(
            candidate,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": subject_url,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
                return response.read(), content_type
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            last_error = exc

    raise last_error
