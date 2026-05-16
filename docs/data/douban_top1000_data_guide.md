# Douban Top1000 Data Guide

This project imports movie data from a UTF-8 CSV file. The recommended working file is:

```text
data/imports/douban_top1000_import.csv
```

## Required Columns

| Column | Required | Format | Notes |
| --- | --- | --- | --- |
| `douban_id` | Recommended | Text | Douban movie ID. Used as the strongest unique key. |
| `title` | Yes | Text | Chinese title or the title shown on Douban. |
| `original_title` | No | Text | Original title. |
| `year` | Recommended | Integer | Release year, for example `1994`. |
| `directors` | Recommended | Semicolon list | Example: `Christopher Nolan;Jonathan Nolan`. |
| `actors` | Recommended | Semicolon list | Main cast only; 3 to 6 names is enough. |
| `genres` | Yes | Semicolon list | Example: `剧情;犯罪;悬疑`. |
| `countries` | Recommended | Semicolon list | Example: `美国;英国`. |
| `rating` | Yes | Decimal 0-10 | Douban score, for example `9.4`. |
| `rating_count` | Recommended | Integer | Number of Douban ratings. |
| `rank` | Yes | Integer 1-1000 | Douban Top1000 rank. Must be unique. |
| `poster_url` | No | URL | Can be blank. |
| `summary` | Recommended | Text | Short plot summary. Keep it concise. |
| `main_category` | Recommended | Category code | If blank, the importer infers it from `genres`. |
| `feature_tags` | Recommended | Semicolon list | Tags used by the recommender, for example `反转;烧脑;高分`. |

## Five Category Codes

Use these exact codes in `main_category`:

```text
suspense_crime
romance_drama
comedy_animation
sci_fi_action
history_war_biography
```

Reference file:

```text
data/reference/douban_top1000_categories.csv
```

## Data Cleaning Rules

1. Save the file as `UTF-8` or `UTF-8 with BOM`.
2. Use semicolons (`;`) for list fields such as `genres`, `directors`, `actors`, `countries`, and `feature_tags`.
3. Keep `rank` unique from `1` to `1000`.
4. Keep `douban_id` unique when present.
5. If a movie has mixed genres, choose the category that best represents why a user would like it.
6. For recommendation quality, keep at least 20 movies in each category; 100 to 300 per category is better for Top1000 data.

## Validate Before Import

Draft template check:

```bash
python manage.py validate_movie_csv data/imports/douban_top1000_import.csv --allow-draft
```

Final Top1000 check:

```bash
python manage.py validate_movie_csv data/imports/douban_top1000_import.csv --expect-count 1000
```

Import after validation passes:

```bash
python manage.py import_movies data/imports/douban_top1000_import.csv
```

## Recommended Workflow

1. Fill `douban_id`, `title`, `year`, `genres`, `rating`, and `rank` first.
2. Fill `main_category` using the category reference.
3. Add `feature_tags` for recommendation accuracy.
4. Run the draft validator.
5. Fill missing summaries, directors, actors, countries, and rating counts.
6. Run the final validator.
7. Import into Django/Supabase.
