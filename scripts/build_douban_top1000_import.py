import argparse
import csv
from pathlib import Path


OUTPUT_HEADERS = [
    "douban_id",
    "title",
    "original_title",
    "year",
    "directors",
    "actors",
    "genres",
    "countries",
    "rating",
    "rating_count",
    "rank",
    "poster_url",
    "summary",
    "main_category",
    "feature_tags",
]

SOURCE_FILES = [
    "douban_all_movies.csv",
    "douban_top250_movies.csv",
    "douban_high_rating.csv",
    "douban_chinese_movies.csv",
    "douban_western_movies.csv",
    "douban_japanese_movies.csv",
    "douban_hongkong_movies.csv",
]

CATEGORY_PRIORITY = [
    ("suspense_crime", {"悬疑", "犯罪", "惊悚", "黑色电影"}),
    ("comedy_animation", {"喜剧", "动画", "儿童", "家庭"}),
    ("history_war_biography", {"历史", "战争", "传记", "纪录片", "古装"}),
    ("sci_fi_action", {"科幻", "动作", "冒险", "奇幻", "灾难", "武侠"}),
    ("romance_drama", {"爱情", "剧情", "文艺", "青春", "音乐", "同性"}),
]


def main():
    parser = argparse.ArgumentParser(
        description="Build project-ready Douban Top1000 import CSV from the public dataset."
    )
    parser.add_argument("source_dir", type=Path, help="Directory containing douban_*.csv source files.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/imports/douban_top1000_import.csv"),
        help="Output CSV path.",
    )
    parser.add_argument("--limit", type=int, default=1000)
    args = parser.parse_args()

    movies = load_movies(args.source_dir)
    top250_ids = load_top250_ids(args.source_dir / "douban_top250_movies.csv")
    ranked = rank_movies(movies, top250_ids, args.limit)
    rows = [to_import_row(movie, rank) for rank, movie in enumerate(ranked, start=1)]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {args.output}")


def load_movies(source_dir):
    movies = {}
    for file_name in SOURCE_FILES:
        path = source_dir / file_name
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                movie_id = clean(row.get("movie_id"))
                if not movie_id:
                    continue
                current = movies.get(movie_id)
                if current is None or source_quality(row) > source_quality(current):
                    movies[movie_id] = row
    return movies


def load_top250_ids(path):
    if not path.exists():
        return []
    ids = []
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            movie_id = clean(row.get("movie_id"))
            if movie_id:
                ids.append(movie_id)
    return ids


def rank_movies(movies, top250_ids, limit):
    top250_rank = {movie_id: index for index, movie_id in enumerate(top250_ids)}
    candidates = [
        movie
        for movie in movies.values()
        if title_for_sort(movie) and safe_float(movie.get("rating")) > 0 and split_list(movie.get("genres"))
    ]

    def sort_key(movie):
        movie_id = clean(movie.get("movie_id"))
        official_rank = top250_rank.get(movie_id, 10_000)
        return (
            official_rank,
            -safe_float(movie.get("rating")),
            -safe_int(movie.get("total_ratings")),
            title_for_sort(movie),
        )

    ranked = sorted(candidates, key=sort_key)
    return ranked[:limit]


def to_import_row(movie, rank):
    genres = split_list(movie.get("genres"))
    countries = split_list(movie.get("countries"))
    tags = split_list(movie.get("tags"))
    directors = split_list(movie.get("directors"))
    actors = split_list(movie.get("actors"))
    year = extract_year(movie.get("release_date"))
    feature_tags = build_feature_tags(genres, tags, directors[:1], countries[:1])

    return {
        "douban_id": clean(movie.get("movie_id")),
        "title": clean(movie.get("title") or movie.get("\ufefftitle")),
        "original_title": "",
        "year": year,
        "directors": join_list(directors),
        "actors": join_list(actors[:6]),
        "genres": join_list(genres),
        "countries": join_list(countries),
        "rating": clean(movie.get("rating")),
        "rating_count": safe_int(movie.get("total_ratings")),
        "rank": rank,
        "poster_url": clean(movie.get("poster")),
        "summary": clean(movie.get("summary")),
        "main_category": classify_category(genres),
        "feature_tags": join_list(feature_tags),
    }


def classify_category(genres):
    genre_set = set(genres)
    best_category = "romance_drama"
    best_score = 0
    for category, keywords in CATEGORY_PRIORITY:
        score = len(genre_set & keywords)
        if score > best_score:
            best_category = category
            best_score = score
    return best_category


def build_feature_tags(*groups):
    tags = []
    seen = set()
    for group in groups:
        for value in group:
            value = clean(value)
            if value and value not in seen:
                tags.append(value)
                seen.add(value)
    if "高分" not in seen:
        tags.append("高分")
    return tags[:12]


def split_list(value):
    value = clean(value)
    if not value:
        return []
    normalized = (
        value.replace(" / ", ";")
        .replace("/", ";")
        .replace("，", ";")
        .replace(",", ";")
    )
    return [part.strip() for part in normalized.split(";") if part.strip()]


def join_list(values):
    return ";".join(clean(value) for value in values if clean(value))


def extract_year(value):
    value = clean(value)
    if len(value) >= 4 and value[:4].isdigit():
        return value[:4]
    return ""


def source_quality(row):
    return (
        bool(clean(row.get("summary"))),
        bool(clean(row.get("poster"))),
        safe_int(row.get("total_ratings")),
    )


def safe_int(value):
    try:
        return int(float(clean(value)))
    except (TypeError, ValueError):
        return 0


def safe_float(value):
    try:
        return float(clean(value))
    except (TypeError, ValueError):
        return 0.0


def title_for_sort(row):
    return clean(row.get("title") or row.get("\ufefftitle"))


def clean(value):
    return str(value or "").strip()


if __name__ == "__main__":
    main()
