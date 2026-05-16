# Movie Blog Recommender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable Django + Supabase-ready movie blog recommender MVP with sample data, five category rating forms, TaskCF-style recommendation services, and a complete anonymous user flow.

**Architecture:** Django renders the user-facing pages and owns all business logic. Supabase is used as PostgreSQL storage through Django's database connection; local SQLite is supported as a development fallback when Supabase credentials are not present. Recommendation logic lives in small service modules so it can be tested independently from views and database setup.

**Tech Stack:** Python 3, Django, PostgreSQL-compatible models, pytest/unittest-style Django tests, CSV import command, HTML templates, plain CSS.

---

## File Structure

Create and modify these files:

```text
requirements.txt
.env.example
.gitignore
manage.py
config/__init__.py
config/settings.py
config/urls.py
config/wsgi.py
config/asgi.py
apps/__init__.py
apps/blog/__init__.py
apps/blog/apps.py
apps/blog/views.py
apps/blog/urls.py
apps/movies/__init__.py
apps/movies/apps.py
apps/movies/models.py
apps/movies/admin.py
apps/movies/services/classifier.py
apps/movies/services/feature_builder.py
apps/movies/management/commands/import_movies.py
apps/ratings/__init__.py
apps/ratings/apps.py
apps/ratings/models.py
apps/ratings/admin.py
apps/ratings/forms.py
apps/ratings/views.py
apps/ratings/urls.py
apps/ratings/services/session_service.py
apps/recommendations/__init__.py
apps/recommendations/apps.py
apps/recommendations/models.py
apps/recommendations/admin.py
apps/recommendations/services/parameter_selector.py
apps/recommendations/services/similarity.py
apps/recommendations/services/reason_generator.py
apps/recommendations/services/recommender.py
templates/base.html
templates/blog/home.html
templates/ratings/select_category.html
templates/ratings/rating_form.html
templates/recommendations/result.html
static/css/site.css
data/templates/douban_top1000_template.csv
data/samples/sample_movies.csv
tests/test_classifier.py
tests/test_similarity.py
tests/test_parameter_selector.py
tests/test_reason_generator.py
tests/test_recommender.py
tests/test_import_movies.py
tests/test_user_flow.py
```

## Task 1: Project Bootstrap

**Files:**
- Create: all Django project package files, requirements, env sample, gitignore
- Test: `python manage.py check`

- [ ] **Step 1: Create baseline Django files**

Create the package layout and minimal settings. `config/settings.py` must read Supabase database values from environment variables and fall back to SQLite when `SUPABASE_DB_HOST` is empty.

- [ ] **Step 2: Run Django system check**

Run: `python manage.py check`

Expected: `System check identified no issues`.

## Task 2: Movie Classification and Feature Helpers

**Files:**
- Create: `apps/movies/services/classifier.py`
- Create: `apps/movies/services/feature_builder.py`
- Test: `tests/test_classifier.py`

- [ ] **Step 1: Write failing tests**

`tests/test_classifier.py` verifies:

```python
from apps.movies.services.classifier import (
    CATEGORY_LABELS,
    classify_main_category,
    normalize_category,
)


def test_normalize_category_accepts_known_code():
    assert normalize_category("suspense_crime") == "suspense_crime"


def test_classify_main_category_prefers_suspense_crime():
    assert classify_main_category(["剧情", "犯罪", "悬疑"]) == "suspense_crime"


def test_category_labels_include_five_categories():
    assert len(CATEGORY_LABELS) == 5
    assert CATEGORY_LABELS["romance_drama"] == "爱情剧情"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test tests.test_classifier -v 2`

Expected: FAIL because `apps.movies.services.classifier` does not exist.

- [ ] **Step 3: Implement classifier and feature helpers**

Implement constants for the five category codes and functions that normalize known category codes, infer a category from genre tags, and build feature tags from genres, directors, actors, countries, and summary keywords.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test tests.test_classifier -v 2`

Expected: PASS.

## Task 3: Data Models

**Files:**
- Create: `apps/movies/models.py`
- Create: `apps/ratings/models.py`
- Create: `apps/recommendations/models.py`
- Create: admin registrations
- Test: `python manage.py makemigrations --check --dry-run`

- [ ] **Step 1: Write model code**

Create Django models for `Movie`, `RatingForm`, `RatingFormMovie`, `UserSession`, `UserRating`, and `RecommendationResult`. Use JSONField for list-like metadata, explicit category choices, rating validators, uniqueness constraints for repeated ratings and recommendation ranks, and stable `session_key` storage.

- [ ] **Step 2: Check migrations can be generated**

Run: `python manage.py makemigrations --check --dry-run`

Expected: non-zero exit indicating model changes need migrations.

- [ ] **Step 3: Generate migrations**

Run: `python manage.py makemigrations`

Expected: migrations are created for `movies`, `ratings`, and `recommendations`.

- [ ] **Step 4: Apply migrations**

Run: `python manage.py migrate`

Expected: all migrations apply successfully using SQLite fallback unless Supabase env vars are configured.

## Task 4: Recommendation Service Unit Tests

**Files:**
- Create: `apps/recommendations/services/parameter_selector.py`
- Create: `apps/recommendations/services/similarity.py`
- Create: `apps/recommendations/services/reason_generator.py`
- Test: `tests/test_similarity.py`, `tests/test_parameter_selector.py`, `tests/test_reason_generator.py`

- [ ] **Step 1: Write failing tests**

Tests verify:

```python
from apps.recommendations.services.parameter_selector import choose_parameter_group
from apps.recommendations.services.similarity import jaccard_similarity, normalize_douban_rating
from apps.recommendations.services.reason_generator import generate_reason


def test_jaccard_similarity_scores_overlap():
    assert jaccard_similarity(["悬疑", "犯罪"], ["犯罪", "剧情"]) == 0.3333333333333333


def test_normalize_douban_rating_bounds_value():
    assert normalize_douban_rating(9.8) == 1.0
    assert normalize_douban_rating(7.0) == 0.0


def test_choose_parameter_group_uses_type_first_for_few_ratings():
    params = choose_parameter_group([5, 4, 3, 4, 5, 3, 4, 5])
    assert params.name == "type_first"


def test_generate_reason_mentions_source_movie_and_tags():
    reason = generate_reason("致命魔术", ["盗梦空间"], ["悬疑", "反转"], "悬疑犯罪", 8.9)
    assert "盗梦空间" in reason
    assert "悬疑" in reason
    assert "豆瓣评分较高" in reason
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python manage.py test tests.test_similarity tests.test_parameter_selector tests.test_reason_generator -v 2`

Expected: FAIL because service modules are missing.

- [ ] **Step 3: Implement minimal services**

Implement Jaccard overlap, rating/rank normalization, parameter group selection, and rule-based recommendation reason generation.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python manage.py test tests.test_similarity tests.test_parameter_selector tests.test_reason_generator -v 2`

Expected: PASS.

## Task 5: End-to-End Recommender Service

**Files:**
- Create: `apps/recommendations/services/recommender.py`
- Test: `tests/test_recommender.py`

- [ ] **Step 1: Write failing tests**

`tests/test_recommender.py` creates sample movies, one rating form, a user session, and ratings. It verifies `recommend_movies(session)` returns 20 or fewer results, excludes rated movies, saves `RecommendationResult` rows, and ranks movies by score.

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test tests.test_recommender -v 2`

Expected: FAIL because `recommend_movies` does not exist.

- [ ] **Step 3: Implement recommender**

Implement:

```text
build_user_preference
score_candidate_movie
apply_diversity_filter
recommend_movies
```

Use the scoring formula from the design document and save algorithm version `taskcf_v1`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test tests.test_recommender -v 2`

Expected: PASS.

## Task 6: CSV Template and Import Command

**Files:**
- Create: `data/templates/douban_top1000_template.csv`
- Create: `data/samples/sample_movies.csv`
- Create: `apps/movies/management/commands/import_movies.py`
- Test: `tests/test_import_movies.py`

- [ ] **Step 1: Write failing import tests**

The test copies `data/samples/sample_movies.csv`, runs:

```python
call_command("import_movies", str(sample_path))
```

It verifies movies are created, categories are normalized, feature tags are populated, five rating forms exist, and each form has sample movies where data is available.

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test tests.test_import_movies -v 2`

Expected: FAIL because import command does not exist.

- [ ] **Step 3: Implement CSV files and command**

Create the CSV template header and sample data with at least 25 movies across five categories. Implement idempotent import using `douban_id` when present and `title + year` as fallback.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test tests.test_import_movies -v 2`

Expected: PASS.

## Task 7: Anonymous User Flow Views

**Files:**
- Create: `apps/blog/views.py`, `apps/blog/urls.py`
- Create: `apps/ratings/forms.py`, `apps/ratings/views.py`, `apps/ratings/urls.py`
- Modify: `config/urls.py`
- Create: HTML templates
- Test: `tests/test_user_flow.py`

- [ ] **Step 1: Write failing flow tests**

Tests verify:

```text
GET / returns 200.
GET /recommend/category/ returns 200 and lists five categories.
POST /recommend/category/ creates a session and redirects to rating form.
POST /recommend/rate/<session_key>/ with fewer than 8 ratings returns validation error.
POST /recommend/rate/<session_key>/ with enough ratings redirects to result page.
GET /recommend/result/<session_key>/ returns saved recommendation results.
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python manage.py test tests.test_user_flow -v 2`

Expected: FAIL because URLs and views do not exist.

- [ ] **Step 3: Implement views and templates**

Implement server-rendered views, form validation, session lookup, rating save, recommendation call, and result rendering.

- [ ] **Step 4: Run test to verify it passes**

Run: `python manage.py test tests.test_user_flow -v 2`

Expected: PASS.

## Task 8: Styling and Local Demo Verification

**Files:**
- Create: `static/css/site.css`
- Modify: templates to load CSS

- [ ] **Step 1: Add restrained UI styling**

Use a readable blog/app hybrid layout with compact cards, accessible buttons, and responsive rating controls.

- [ ] **Step 2: Load sample data**

Run: `python manage.py import_movies data/samples/sample_movies.csv`

Expected: sample movies and rating forms are created.

- [ ] **Step 3: Start development server**

Run: `python manage.py runserver 127.0.0.1:8000`

Expected: local server starts.

- [ ] **Step 4: Verify in browser or with HTTP checks**

Open `http://127.0.0.1:8000/` and complete one recommendation flow. If browser verification is unavailable, run Django tests and use the test client coverage as verification evidence.

## Self-Review Checklist

- Spec coverage: The plan covers project bootstrap, database models, data import, five category flow, TaskCF services, anonymous sessions, recommendation results, templates, and tests.
- Placeholder scan: The plan contains no TBD/TODO placeholders.
- Type consistency: Category code names, model names, service names, and URL names match the design document.
