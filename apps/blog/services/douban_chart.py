import datetime
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from django.db import transaction
from django.utils import timezone

from apps.blog.models import DoubanChartMovie


DOUBAN_CHART_URL = "https://movie.douban.com/chart"
SYNC_INTERVAL = datetime.timedelta(days=3)


@dataclass(frozen=True)
class DoubanChartEntry:
    douban_id: str
    rank: int
    title: str
    subtitle: str
    info_text: str
    rating: Decimal | None
    rating_count: int
    poster_url: str
    subject_url: str


@dataclass(frozen=True)
class DoubanChartSyncResult:
    status: str
    updated_count: int
    message: str


class DoubanChartParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.entries = []
        self.current = None
        self.capture = None
        self.capture_parts = []
        self.link_texts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        class_names = set((attrs.get("class") or "").split())
        if tag == "tr" and "item" in class_names:
            self.current = {
                "rank": len(self.entries) + 1,
                "poster_url": "",
                "subject_url": "",
                "douban_id": "",
                "info_text": "",
                "rating": None,
                "rating_count": 0,
            }
            self.link_texts = []
            return

        if self.current is None:
            return

        if tag == "a":
            href = attrs.get("href", "")
            if "/subject/" in href:
                self.current["subject_url"] = self.current["subject_url"] or href
                match = re.search(r"/subject/(\d+)/", href)
                if match:
                    self.current["douban_id"] = self.current["douban_id"] or match.group(1)
                self.capture = "link"
                self.capture_parts = []
        elif tag == "img" and not self.current["poster_url"]:
            self.current["poster_url"] = attrs.get("src", "")
        elif tag == "p" and "pl" in class_names:
            self.capture = "info"
            self.capture_parts = []
        elif tag == "span" and "rating_nums" in class_names:
            self.capture = "rating"
            self.capture_parts = []
        elif tag == "span" and "pl" in class_names:
            self.capture = "rating_count"
            self.capture_parts = []

    def handle_data(self, data):
        if self.capture:
            self.capture_parts.append(data)

    def handle_endtag(self, tag):
        if self.current is None:
            return

        if self.capture == "link" and tag == "a":
            text = clean_text("".join(self.capture_parts))
            if text:
                self.link_texts.append(text)
            self.capture = None
            self.capture_parts = []
        elif self.capture == "info" and tag == "p":
            self.current["info_text"] = clean_text("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif self.capture == "rating" and tag == "span":
            self.current["rating"] = parse_decimal("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif self.capture == "rating_count" and tag == "span":
            self.current["rating_count"] = parse_rating_count("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif tag == "tr":
            entry = build_entry(self.current, self.link_texts)
            if entry is not None:
                self.entries.append(entry)
            self.current = None
            self.capture = None
            self.capture_parts = []
            self.link_texts = []


def clean_text(value):
    return re.sub(r"\s+", " ", value).strip()


def parse_decimal(value):
    value = clean_text(value)
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def parse_rating_count(value):
    match = re.search(r"(\d+)", value.replace(",", ""))
    return int(match.group(1)) if match else 0


def split_title(text):
    parts = [part.strip() for part in text.split("/") if part.strip()]
    if not parts:
        return "", ""
    return parts[0], " / ".join(parts[1:])


def build_entry(raw_entry, link_texts):
    title_text = max(link_texts, key=len) if link_texts else ""
    title, subtitle = split_title(title_text)
    if not raw_entry["douban_id"] or not title:
        return None
    return DoubanChartEntry(
        douban_id=raw_entry["douban_id"],
        rank=raw_entry["rank"],
        title=title,
        subtitle=subtitle,
        info_text=raw_entry["info_text"],
        rating=raw_entry["rating"],
        rating_count=raw_entry["rating_count"],
        poster_url=raw_entry["poster_url"],
        subject_url=raw_entry["subject_url"],
    )


def parse_douban_chart(html):
    parser = DoubanChartParser()
    parser.feed(html)
    parser.close()
    return parser.entries


def fetch_douban_chart_html():
    request = urllib.request.Request(
        DOUBAN_CHART_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://movie.douban.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_douban_chart_poster(movie):
    request = urllib.request.Request(
        movie.poster_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": movie.subject_url,
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        content_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        return response.read(), content_type


def get_homepage_douban_chart(limit=6):
    return list(DoubanChartMovie.objects.filter(is_active=True).order_by("rank", "title")[:limit])


def sync_douban_chart(fetch_html=fetch_douban_chart_html, force=False):
    latest_fetch = (
        DoubanChartMovie.objects.filter(is_active=True)
        .exclude(fetched_at__isnull=True)
        .order_by("-fetched_at")
        .values_list("fetched_at", flat=True)
        .first()
    )
    if not force and latest_fetch and timezone.now() - latest_fetch < SYNC_INTERVAL:
        return DoubanChartSyncResult("skipped", 0, "Douban chart data is newer than 3 days.")

    try:
        entries = parse_douban_chart(fetch_html())
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return DoubanChartSyncResult("failed", 0, f"Failed to fetch Douban chart: {exc}")

    if not entries:
        return DoubanChartSyncResult("failed", 0, "No Douban chart movies were parsed.")

    fetched_at = timezone.now()
    active_ids = [entry.douban_id for entry in entries]
    with transaction.atomic():
        for entry in entries:
            DoubanChartMovie.objects.update_or_create(
                douban_id=entry.douban_id,
                defaults={
                    "rank": entry.rank,
                    "title": entry.title,
                    "subtitle": entry.subtitle,
                    "info_text": entry.info_text,
                    "rating": entry.rating,
                    "rating_count": entry.rating_count,
                    "poster_url": entry.poster_url,
                    "subject_url": entry.subject_url,
                    "fetched_at": fetched_at,
                    "is_active": True,
                },
            )
        DoubanChartMovie.objects.exclude(douban_id__in=active_ids).update(is_active=False)

    return DoubanChartSyncResult("updated", len(entries), f"Updated {len(entries)} Douban chart movies.")
