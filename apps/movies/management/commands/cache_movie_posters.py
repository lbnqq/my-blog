from django.core.management.base import BaseCommand

from apps.blog.services.poster_fetcher import fetch_douban_poster
from apps.movies.models import Movie
from apps.movies.templatetags.movie_posters import poster_cache_path


class Command(BaseCommand):
    help = "Download remote movie posters into static/img/posters for stable local display."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--rank-lte", type=int, default=100)
        parser.add_argument("--overwrite", action="store_true")

    def handle(self, *args, **options):
        queryset = Movie.objects.exclude(poster_url="").order_by("rank", "title")
        rank_lte = options["rank_lte"]
        if rank_lte:
            queryset = queryset.filter(rank__lte=rank_lte)
        queryset = queryset[: options["limit"]]

        downloaded = 0
        skipped = 0
        failed = 0
        for movie in queryset:
            target_path = poster_cache_path(movie)
            if target_path is None:
                skipped += 1
                continue
            if target_path.exists() and not options["overwrite"]:
                skipped += 1
                continue

            try:
                self.download(movie.poster_url, target_path)
            except (OSError, TimeoutError) as exc:
                failed += 1
                self.stderr.write(f"Failed {movie.title}: {exc}")
                continue

            downloaded += 1
            self.stdout.write(f"Cached {movie.title} -> {target_path}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Poster cache complete: {downloaded} downloaded, {skipped} skipped, {failed} failed."
            )
        )

    def download(self, url, target_path):
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content, _ = fetch_douban_poster(url, "https://movie.douban.com/")
        target_path.write_bytes(content)
