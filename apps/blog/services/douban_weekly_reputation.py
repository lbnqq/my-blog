import datetime
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal
from html.parser import HTMLParser

from django.db import transaction
from django.utils import timezone

from apps.blog.models import DoubanWeeklyReputationMovie
from apps.blog.services.douban_chart import clean_text, parse_decimal, parse_rating_count


DOUBAN_CHART_URL = "https://movie.douban.com/chart"
SYNC_INTERVAL = datetime.timedelta(days=7)


@dataclass(frozen=True)
class WeeklyReputationEntry:
    douban_id: str
    rank: int
    title: str
    subject_url: str


@dataclass(frozen=True)
class SubjectDetail:
    title: str
    subtitle: str
    info_text: str
    rating: Decimal | None
    rating_count: int
    poster_url: str


@dataclass(frozen=True)
class WeeklyReputationSyncResult:
    status: str
    updated_count: int
    message: str


class WeeklyReputationChartParser(HTMLParser):
    def __init__(self, limit):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.entries = []
        self.in_weekly_section = False
        self.capture_heading = False
        self.capture_link = None
        self.capture_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"h2", "h3", "h4"}:
            self.capture_heading = True
            self.capture_parts = []
            return

        if not self.in_weekly_section or len(self.entries) >= self.limit:
            return

        if tag == "a":
            href = attrs.get("href", "")
            match = re.search(r"https://movie\.douban\.com/subject/(\d+)/", href)
            if match:
                self.capture_link = {
                    "douban_id": match.group(1),
                    "subject_url": href,
                }
                self.capture_parts = []

    def handle_data(self, data):
        if self.capture_heading or self.capture_link:
            self.capture_parts.append(data)

    def handle_endtag(self, tag):
        if self.capture_heading and tag in {"h2", "h3", "h4"}:
            heading = clean_text("".join(self.capture_parts))
            if "一周口碑榜" in heading:
                self.in_weekly_section = True
            elif self.in_weekly_section:
                self.in_weekly_section = False
            self.capture_heading = False
            self.capture_parts = []
            return

        if self.capture_link and tag == "a":
            title = clean_text("".join(self.capture_parts))
            if title and len(self.entries) < self.limit:
                self.entries.append(
                    WeeklyReputationEntry(
                        douban_id=self.capture_link["douban_id"],
                        rank=len(self.entries) + 1,
                        title=title,
                        subject_url=self.capture_link["subject_url"],
                    )
                )
            self.capture_link = None
            self.capture_parts = []


class SubjectDetailParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title_text = ""
        self.poster_url = ""
        self.info_parts = []
        self.rating = None
        self.rating_count = 0
        self.in_mainpic = False
        self.in_info = False
        self.capture = None
        self.capture_parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        class_names = set((attrs.get("class") or "").split())
        if tag == "div" and attrs.get("id") == "mainpic":
            self.in_mainpic = True
        elif tag == "div" and attrs.get("id") == "info":
            self.in_info = True
        elif tag == "img" and self.in_mainpic and not self.poster_url:
            self.poster_url = attrs.get("src", "")
        elif tag == "br" and self.in_info:
            self.info_parts.append(" / ")
        elif tag == "span" and attrs.get("property") == "v:itemreviewed":
            self.capture = "title"
            self.capture_parts = []
        elif tag == "strong" and "rating_num" in class_names:
            self.capture = "rating"
            self.capture_parts = []
        elif tag == "span" and attrs.get("property") == "v:votes":
            self.capture = "votes"
            self.capture_parts = []

    def handle_data(self, data):
        if self.capture:
            self.capture_parts.append(data)
        elif self.in_info:
            text = clean_text(data)
            if text:
                self.info_parts.append(text)

    def handle_endtag(self, tag):
        if self.capture == "title" and tag == "span":
            self.title_text = clean_text("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif self.capture == "rating" and tag == "strong":
            self.rating = parse_decimal("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif self.capture == "votes" and tag == "span":
            self.rating_count = parse_rating_count("".join(self.capture_parts))
            self.capture = None
            self.capture_parts = []
        elif self.in_mainpic and tag == "div":
            self.in_mainpic = False
        elif self.in_info and tag == "div":
            self.in_info = False


def parse_weekly_reputation_chart(html, limit=6):
    parser = WeeklyReputationChartParser(limit=limit)
    parser.feed(html)
    parser.close()
    return parser.entries


def split_subject_title(title_text):
    match = re.match(r"^(.+?)\s+([A-Za-z].*)$", title_text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return title_text, ""


def normalize_info_text(parts):
    text = clean_text(" ".join(parts))
    text = re.sub(r"\s*/\s*/\s*", " / ", text)
    text = re.sub(r"\s*:\s*", ": ", text)
    return clean_text(text).strip(" /")


def parse_subject_detail(html):
    if html.lstrip().startswith("{"):
        return parse_subject_json(html)
    parser = SubjectDetailParser()
    parser.feed(html)
    parser.close()
    title, subtitle = split_subject_title(parser.title_text)
    return SubjectDetail(
        title=title,
        subtitle=subtitle,
        info_text=normalize_info_text(parser.info_parts),
        rating=parser.rating,
        rating_count=parser.rating_count,
        poster_url=parser.poster_url,
    )


def parse_subject_json(raw_json):
    data = json.loads(raw_json)
    title = data.get("title", "").strip()
    aka = data.get("aka") or []
    year = str(data.get("year") or "").strip()
    subtitle = aka[0].strip() if aka else ""
    if subtitle and year:
        subtitle = f"{subtitle} ({year})"
    rating_data = data.get("rating") or {}
    poster_url = (
        data.get("cover", {})
        .get("image", {})
        .get("normal", {})
        .get("url", "")
        .replace("\\/", "/")
    )
    rating = parse_decimal(str(rating_data.get("value", "")))
    rating_count = int(rating_data.get("count") or 0)
    return SubjectDetail(
        title=title,
        subtitle=subtitle,
        info_text=clean_text(data.get("card_subtitle", "")),
        rating=rating,
        rating_count=rating_count,
        poster_url=poster_url,
    )


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


def fetch_subject_html(subject_url):
    match = re.search(r"/subject/(\d+)/", subject_url)
    subject_id = match.group(1) if match else subject_url.rstrip("/").split("/")[-1]
    api_url = f"https://m.douban.com/rexxar/api/v2/movie/{subject_id}"
    request = urllib.request.Request(
        api_url,
        headers={
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": subject_url,
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_douban_weekly_reputation_poster(movie):
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


def get_homepage_weekly_reputation(limit=6):
    return list(DoubanWeeklyReputationMovie.objects.filter(is_active=True).order_by("rank", "title")[:limit])


def sync_douban_weekly_reputation(
    fetch_chart_html=fetch_douban_chart_html,
    fetch_subject_html=fetch_subject_html,
    force=False,
):
    latest_fetch = (
        DoubanWeeklyReputationMovie.objects.filter(is_active=True)
        .exclude(fetched_at__isnull=True)
        .order_by("-fetched_at")
        .values_list("fetched_at", flat=True)
        .first()
    )
    if not force and latest_fetch and timezone.now() - latest_fetch < SYNC_INTERVAL:
        return WeeklyReputationSyncResult("skipped", 0, "Douban weekly reputation data is newer than 7 days.")

    try:
        entries = parse_weekly_reputation_chart(fetch_chart_html(), limit=6)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        return WeeklyReputationSyncResult("failed", 0, f"Failed to fetch Douban weekly reputation chart: {exc}")

    if not entries:
        return WeeklyReputationSyncResult("failed", 0, "No Douban weekly reputation movies were parsed.")

    enriched_entries = []
    for entry in entries:
        try:
            detail = parse_subject_detail(fetch_subject_html(entry.subject_url))
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            detail = SubjectDetail(entry.title, "", "", None, 0, "")
        enriched_entries.append((entry, detail))

    fetched_at = timezone.now()
    active_ids = [entry.douban_id for entry, _detail in enriched_entries]
    with transaction.atomic():
        for entry, detail in enriched_entries:
            DoubanWeeklyReputationMovie.objects.update_or_create(
                douban_id=entry.douban_id,
                defaults={
                    "rank": entry.rank,
                    "title": detail.title or entry.title,
                    "subtitle": detail.subtitle,
                    "info_text": detail.info_text,
                    "rating": detail.rating,
                    "rating_count": detail.rating_count,
                    "poster_url": detail.poster_url,
                    "subject_url": entry.subject_url,
                    "fetched_at": fetched_at,
                    "is_active": True,
                },
            )
        DoubanWeeklyReputationMovie.objects.exclude(douban_id__in=active_ids).update(is_active=False)

    return WeeklyReputationSyncResult("updated", len(enriched_entries), f"Updated {len(enriched_entries)} Douban weekly reputation movies.")
