from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.utils import DatabaseError
from django.utils import timezone

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie
from apps.blog.services.douban_chart import get_homepage_douban_chart, sync_douban_chart
from apps.blog.services.douban_weekly_reputation import (
    get_homepage_weekly_reputation,
    sync_douban_weekly_reputation,
)
from apps.movies.models import Movie
from apps.movies.services.classifier import CATEGORY_LABELS
from apps.movies.services.daily_movie import get_daily_movie
from apps.ratings.models import RatingForm, UserRating
from apps.ratings.services.rating_form_service import get_active_form_for_category
from apps.ratings.services.session_service import create_user_session
from apps.recommendations.services.recommender import recommend_movies


class Command(BaseCommand):
    help = "OpenCLI entrypoint for the movie blog workflows."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command")

        subparsers.add_parser("home", help="Show homepage content.")

        sync_parser = subparsers.add_parser("sync", help="Sync Douban homepage charts.")
        sync_parser.add_argument("--chart", action="store_true", help="Sync only the Douban movie chart.")
        sync_parser.add_argument("--weekly", action="store_true", help="Sync only the weekly reputation chart.")
        sync_parser.add_argument("--force", action="store_true", help="Fetch even when local data is fresh.")

        movies_parser = subparsers.add_parser("movies", help="Manage local movie data.")
        movies_subparsers = movies_parser.add_subparsers(dest="movies_command")

        import_parser = movies_subparsers.add_parser("import", help="Import Douban Top1000 CSV data.")
        import_parser.add_argument("csv_path")

        validate_parser = movies_subparsers.add_parser("validate", help="Validate Douban Top1000 CSV data.")
        validate_parser.add_argument("csv_path")
        validate_parser.add_argument("--expect-count", type=int, default=1000)
        validate_parser.add_argument("--allow-draft", action="store_true")

        search_parser = movies_subparsers.add_parser("search", help="Search local movies.")
        search_parser.add_argument("keyword")
        search_parser.add_argument("--limit", type=int, default=10)

        show_parser = movies_subparsers.add_parser("show", help="Show one local movie.")
        show_parser.add_argument("identifier", help="Movie primary key or Douban id.")

        recommend_parser = subparsers.add_parser("recommend", help="Run the recommendation flow.")
        recommend_parser.add_argument("--category", choices=sorted(CATEGORY_LABELS), help="Movie category code.")

        subparsers.add_parser("doctor", help="Check project runtime data health.")

    def handle(self, *args, **options):
        command = options.get("command")
        if command == "home":
            self.handle_home()
        elif command == "sync":
            self.handle_sync(options)
        elif command == "movies":
            self.handle_movies(options)
        elif command == "recommend":
            self.handle_recommend(options)
        elif command == "doctor":
            self.handle_doctor()
        else:
            raise CommandError("Please choose one command: home, sync, movies, recommend, doctor.")

    def handle_home(self):
        self.stdout.write("每日一片")
        daily_movie = get_daily_movie()
        if daily_movie:
            self.write_movie_line(daily_movie)
        else:
            self.stdout.write("  暂无电影数据")

        self.stdout.write("")
        self.stdout.write("豆瓣电影排行榜")
        self.write_douban_rows(self.safe_rows(get_homepage_douban_chart, limit=6))

        self.stdout.write("")
        self.stdout.write("豆瓣一周口碑榜")
        self.write_douban_rows(self.safe_rows(get_homepage_weekly_reputation, limit=6))

    def handle_sync(self, options):
        sync_chart = options["chart"]
        sync_weekly = options["weekly"]
        if not sync_chart and not sync_weekly:
            sync_chart = True
            sync_weekly = True

        if sync_chart:
            result = sync_douban_chart(force=options["force"])
            self.write_sync_result("豆瓣电影排行榜", result)
        if sync_weekly:
            result = sync_douban_weekly_reputation(force=options["force"])
            self.write_sync_result("豆瓣一周口碑榜", result)

    def handle_movies(self, options):
        movies_command = options.get("movies_command")
        if movies_command == "import":
            call_command("import_movies", options["csv_path"], stdout=self.stdout, stderr=self.stderr)
        elif movies_command == "validate":
            call_command(
                "validate_movie_csv",
                options["csv_path"],
                expect_count=options["expect_count"],
                allow_draft=options["allow_draft"],
                stdout=self.stdout,
                stderr=self.stderr,
            )
        elif movies_command == "search":
            self.handle_movies_search(options)
        elif movies_command == "show":
            self.handle_movies_show(options)
        else:
            raise CommandError("Please choose one movies command: import, validate, search, show.")

    def handle_movies_search(self, options):
        keyword = options["keyword"]
        movies = Movie.objects.filter(title__icontains=keyword).order_by("rank", "-rating", "title")[
            : options["limit"]
        ]
        if not movies:
            self.stdout.write(f"未找到电影: {keyword}")
            return
        for movie in movies:
            self.write_movie_line(movie)

    def handle_movies_show(self, options):
        movie = self.find_movie(options["identifier"])
        self.write_movie_line(movie)
        self.stdout.write(f"年份: {movie.year or '未知'}")
        self.stdout.write(f"导演: {', '.join(movie.directors or []) or '未知'}")
        self.stdout.write(f"类型: {', '.join(movie.genres or []) or '未知'}")
        self.stdout.write(f"地区: {', '.join(movie.countries or []) or '未知'}")
        self.stdout.write(f"简介: {movie.summary or '暂无简介'}")

    def handle_recommend(self, options):
        category = options.get("category") or self.prompt_category()
        rating_form = get_active_form_for_category(category)
        if rating_form is None:
            raise CommandError(f"No active rating form for category: {category}")

        form_movies = list(rating_form.form_movies.select_related("movie").all())
        if not form_movies:
            raise CommandError(f"Rating form has no movies for category: {category}")

        session = create_user_session(category)
        ratings = []
        self.stdout.write(f"评分类型: {category} / {CATEGORY_LABELS.get(category, '')}")
        self.stdout.write("请为下面电影输入 1-5 分，直接回车可跳过。至少需要评分 8 部。")

        for form_movie in form_movies:
            movie = form_movie.movie
            self.stdout.write(f"{movie.id}. {movie.title} ({movie.year or '未知'}) 豆瓣 {movie.rating}")
            value = input("评分: ").strip()
            if not value:
                continue
            try:
                rating = int(value)
            except ValueError as exc:
                raise CommandError("评分必须是 1 到 5 的整数。") from exc
            if rating < 1 or rating > 5:
                raise CommandError("评分必须是 1 到 5 的整数。")
            ratings.append(UserRating(session=session, movie=movie, rating=rating))

        if len(ratings) < 8:
            session.delete()
            raise CommandError("请至少评分 8 部电影后再生成推荐。")

        UserRating.objects.bulk_create(ratings)
        results = recommend_movies(session)

        self.stdout.write("")
        self.stdout.write("推荐结果")
        for result in results:
            self.stdout.write(
                f"{result.rank_order}. {result.movie.title} "
                f"({result.movie.year or '未知'}) - {result.reason}"
            )

    def handle_doctor(self):
        database_ok = self.check_database()
        migrations_ok = self.check_migrations()
        movie_count, movie_error = self.safe_count(lambda: Movie.objects.count())
        chart_count, chart_error = self.safe_count(
            lambda: DoubanChartMovie.objects.filter(is_active=True).count()
        )
        weekly_count, weekly_error = self.safe_count(
            lambda: DoubanWeeklyReputationMovie.objects.filter(is_active=True).count()
        )
        active_forms, forms_error = self.safe_count(
            lambda: RatingForm.objects.filter(is_active=True).count()
        )

        self.write_status("数据库连接", database_ok)
        self.write_status("迁移状态", migrations_ok)
        self.write_status("电影数据", database_ok and movie_count > 0, movie_error or f"{movie_count} 部")
        self.write_status("豆瓣电影排行榜", chart_count > 0, chart_error or f"{chart_count} 条 active 数据")
        self.write_status("豆瓣一周口碑榜", weekly_count > 0, weekly_error or f"{weekly_count} 条 active 数据")
        self.write_status(
            "评分表",
            active_forms >= len(CATEGORY_LABELS),
            forms_error or f"{active_forms} 个 active 表",
        )

    def prompt_category(self):
        self.stdout.write("请选择电影类型:")
        categories = list(CATEGORY_LABELS.items())
        for index, (code, label) in enumerate(categories, start=1):
            self.stdout.write(f"{index}. {code} / {label}")
        value = input("类型编号或代码: ").strip()
        if value.isdigit():
            index = int(value)
            if 1 <= index <= len(categories):
                return categories[index - 1][0]
        if value in CATEGORY_LABELS:
            return value
        raise CommandError("未知电影类型。")

    def find_movie(self, identifier):
        queryset = Movie.objects.all()
        movie = None
        if identifier.isdigit():
            movie = queryset.filter(pk=int(identifier)).first()
        if movie is None:
            movie = queryset.filter(douban_id=identifier).first()
        if movie is None:
            raise CommandError(f"Movie not found: {identifier}")
        return movie

    def write_douban_rows(self, movies):
        if isinstance(movies, str):
            self.stdout.write(f"  {movies}")
            return
        movies = list(movies)
        if not movies:
            self.stdout.write("  暂无榜单数据")
            return
        for movie in movies:
            rating = movie.rating if movie.rating is not None else "暂无评分"
            self.stdout.write(
                f"  {movie.rank}. {movie.title} | 豆瓣 {rating} | "
                f"{movie.rating_count} 人评价 | {movie.subject_url}"
            )
            if movie.subtitle:
                self.stdout.write(f"     {movie.subtitle}")
            if movie.info_text:
                self.stdout.write(f"     {movie.info_text}")

    def write_movie_line(self, movie):
        self.stdout.write(
            f"{movie.id}. {movie.title} | douban_id={movie.douban_id or '-'} | "
            f"{movie.year or '未知'} | 豆瓣 {movie.rating} | 排名 {movie.rank or '-'}"
        )

    def write_sync_result(self, label, result):
        message = f"{label}: {result.message}"
        if result.status == "failed":
            self.stderr.write(self.style.WARNING(message))
        else:
            self.stdout.write(self.style.SUCCESS(message))

    def check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            return False
        return True

    def check_migrations(self):
        try:
            executor = MigrationExecutor(connection)
            return not executor.migration_plan(executor.loader.graph.leaf_nodes())
        except Exception:
            return False

    def safe_rows(self, callback, **kwargs):
        try:
            return callback(**kwargs)
        except DatabaseError:
            return "数据表不存在，请先运行数据库迁移: python manage.py migrate"

    def safe_count(self, callback):
        try:
            return callback(), ""
        except DatabaseError:
            return 0, "数据表不存在，请先运行迁移: python manage.py migrate"

    def write_status(self, label, ok, detail=""):
        status = "OK" if ok else "WARN"
        suffix = f" ({detail})" if detail else ""
        self.stdout.write(f"{label}: {status}{suffix}")
