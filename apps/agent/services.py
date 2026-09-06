import json
import uuid
import urllib.error
import urllib.request
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import DoubanChartMovie, DoubanWeeklyReputationMovie
from apps.blog.services.douban_chart import sync_douban_chart
from apps.blog.services.douban_weekly_reputation import sync_douban_weekly_reputation
from apps.movies.models import Movie
from apps.recommendations.models import SyncRun


PENDING_ACTIONS_KEY = "agent_pending_actions"
HISTORY_KEY = "agent_history"
SYNC_COOLDOWN = timedelta(minutes=10)

CATEGORY_LABELS = {
    "suspense_crime": "悬疑犯罪",
    "romance_drama": "爱情剧情",
    "comedy_animation": "喜剧动画",
    "sci_fi_action": "科幻动作冒险",
    "history_war_biography": "历史战争传记",
}


def agent_response(reply, actions=None, requires_confirmation=False, status="ok"):
    return {
        "reply": reply,
        "actions": actions or [],
        "requires_confirmation": requires_confirmation,
        "status": status,
    }


def handle_message(request, message):
    response = answer_message(
        message,
        channel="web",
        allow_write_actions=True,
        request=request,
        absolute_urls=False,
    )
    remember(request, message, response["reply"])
    return response


def answer_feishu_message(message):
    return answer_message(
        message,
        channel="feishu",
        allow_write_actions=False,
        request=None,
        absolute_urls=True,
    )


def answer_message(message, channel, allow_write_actions, request=None, absolute_urls=False):
    message = (message or "").strip()
    if not message:
        return agent_response(
            "你可以问我：这个博客是做什么的、一周口碑榜有哪些、豆瓣排行榜有哪些、搜索电影，或者让我带你去做电影推荐。"
        )

    intent = detect_intent(message)
    if intent == "sync":
        if not allow_write_actions:
            return agent_response(
                "飞书里不能直接执行同步榜单这类写入数据库的操作。请登录网站，在站内电影助手里发起更新并确认执行。"
            )
        return request_sync(request, message)
    if intent == "charts":
        response = get_homepage_charts()
    elif intent == "recommendation":
        response = recommendation_guide(absolute_urls=absolute_urls)
    elif intent == "search":
        response = search_movies(message, absolute_urls=absolute_urls)
    else:
        response = get_blog_intro()

    history = request.session.get(HISTORY_KEY, []) if request is not None else []
    response["reply"] = polish_with_glm(history, message, response["reply"])
    return response


def response_to_feishu_text(response):
    lines = [response.get("reply", "我暂时没有理解这个问题。")]
    for action in response.get("actions", []):
        if action.get("type") == "open_url" and action.get("url"):
            lines.append(f"{action.get('label', '打开链接')}：{action['url']}")
    return "\n".join(lines)


def detect_intent(message):
    lowered = message.lower()
    if any(word in message for word in ["更新", "同步", "刷新"]):
        return "sync"
    if any(word in message for word in ["口碑榜", "排行榜", "榜单", "豆瓣榜"]):
        return "charts"
    if any(word in message for word in ["推荐", "片单", "打分", "评分"]):
        return "recommendation"
    if any(word in message for word in ["搜索", "查找", "找电影"]) or lowered.startswith("search"):
        return "search"
    return "intro"


def get_blog_intro():
    return agent_response(
        "这个博客是一个电影资料馆和个性化推荐系统：首页展示每日电影、一周口碑榜和豆瓣电影排行榜。"
        "用户可以选择电影类型并给代表电影打分，系统会生成 Top20 推荐；推荐结果页还能对推荐电影反馈 1-5 分，"
        "管理员可以在数据中心查看算法效果和数据质量。"
    )


def get_homepage_charts():
    weekly = list(DoubanWeeklyReputationMovie.objects.filter(is_active=True).order_by("rank")[:6])
    chart = list(DoubanChartMovie.objects.filter(is_active=True).order_by("rank")[:6])
    lines = ["当前首页榜单如下："]
    lines.append("一周口碑榜：" + format_chart_rows(weekly))
    lines.append("豆瓣电影排行榜：" + format_chart_rows(chart))
    return agent_response("\n".join(lines))


def format_chart_rows(rows):
    if not rows:
        return "暂无数据。"
    return "；".join(
        f"{movie.rank}. {movie.title}（豆瓣 {movie.rating or '暂无'}，{movie.rating_count} 人评价）"
        for movie in rows
    )


def recommendation_guide(absolute_urls=False):
    category_text = "、".join(CATEGORY_LABELS.values())
    url = build_url(reverse("ratings:category"), absolute=absolute_urls)
    return agent_response(
        f"可以，进入推荐页面后先选择类型（{category_text}），然后至少给 8 部电影打 1-5 分，"
        "系统会生成 Top20 个性化推荐并保存历史。",
        actions=[
            {
                "type": "open_url",
                "label": "进入推荐页面",
                "url": url,
            }
        ],
    )


def search_movies(message, absolute_urls=False):
    keyword = extract_search_keyword(message)
    if not keyword:
        return agent_response("请告诉我要搜索的电影名，例如：搜索电影 霸王别姬。")
    movies = Movie.objects.filter(title__icontains=keyword).order_by("rank", "-rating", "title")[:5]
    if not movies:
        return agent_response(f"我没有在本地电影库找到“{keyword}”。你可以换个片名再试。")
    reply = "找到这些电影：" + "；".join(
        f"{movie.title}（{movie.year or '年份未知'}，豆瓣 {movie.rating}）" for movie in movies
    )
    actions = [
        {
            "type": "open_url",
            "label": f"查看 {movie.title}",
            "url": build_url(reverse("movies:detail", args=[movie.pk]), absolute=absolute_urls),
        }
        for movie in movies[:3]
    ]
    return agent_response(reply, actions=actions)


def extract_search_keyword(message):
    for prefix in ["搜索电影", "搜索", "查找电影", "查找", "找电影", "search"]:
        if message.lower().startswith(prefix.lower()):
            return message[len(prefix) :].strip(" ：:")
    return ""


def build_url(path, absolute=False):
    if not absolute:
        return path
    base_url = getattr(settings, "SITE_PUBLIC_URL", "").strip()
    if not base_url:
        return path
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def request_sync(request, message):
    if request is None or not request.user.is_authenticated:
        return agent_response(
            "同步榜单会写入数据库，需要先登录。登录后再让我更新口碑榜或排行榜即可。",
            actions=[{"type": "open_url", "label": "去登录", "url": reverse("accounts:login")}],
        )

    source = parse_sync_source(message)
    action_id = uuid.uuid4().hex
    pending_actions = request.session.get(PENDING_ACTIONS_KEY, {})
    pending_actions[action_id] = {"type": "sync", "source": source}
    request.session[PENDING_ACTIONS_KEY] = pending_actions
    request.session.modified = True
    label = sync_source_label(source)
    return agent_response(
        f"可以同步{label}。这会抓取外部数据并写入数据库，可能需要一点时间。请确认后执行。",
        actions=[{"type": "confirm_sync", "label": f"确认同步{label}", "action_id": action_id}],
        requires_confirmation=True,
    )


def parse_sync_source(message):
    has_weekly = "口碑" in message
    has_chart = "排行" in message or "豆瓣电影" in message
    wants_all = "全部" in message or ("榜单" in message and not has_weekly and not has_chart)
    if wants_all or (has_weekly and has_chart):
        return "all"
    if has_weekly:
        return SyncRun.Source.WEEKLY_REPUTATION
    if has_chart or "豆瓣" in message:
        return SyncRun.Source.DOUBAN_CHART
    return "all"


def sync_source_label(source):
    if source == SyncRun.Source.WEEKLY_REPUTATION:
        return "一周口碑榜"
    if source == SyncRun.Source.DOUBAN_CHART:
        return "豆瓣电影排行榜"
    return "一周口碑榜和豆瓣电影排行榜"


def execute_pending_action(request, action_id):
    pending_actions = request.session.get(PENDING_ACTIONS_KEY, {})
    action = pending_actions.get(action_id)
    if not action or action.get("type") != "sync":
        return agent_response("这个确认操作已经失效，请重新发送同步请求。", status="error"), 400
    if not request.user.is_authenticated:
        return agent_response("请先登录后再执行同步。", status="error"), 403

    source = action["source"]
    sources = [SyncRun.Source.DOUBAN_CHART, SyncRun.Source.WEEKLY_REPUTATION] if source == "all" else [source]
    blocked = first_blocked_source(request.user, sources)
    if blocked:
        return (
            agent_response(f"{sync_source_label(blocked)}刚刚同步过，请至少等待 10 分钟后再试。", status="rate_limited"),
            429,
        )

    runs = [execute_sync(source_item, request.user) for source_item in sources]
    pending_actions.pop(action_id, None)
    request.session[PENDING_ACTIONS_KEY] = pending_actions
    request.session.modified = True
    failed = [run for run in runs if run.status == SyncRun.Status.FAILED]
    if failed:
        if all(cache_was_retained(run.message) for run in failed):
            labels = "、".join(sync_source_label(run.source) for run in failed)
            return agent_response(
                f"{labels}暂时无法连接豆瓣，已继续使用现有缓存，网站页面仍可正常浏览。"
                "这通常是当前网络或代理到豆瓣的 HTTPS 握手失败导致的，请稍后再试。",
                status="degraded",
            ), 200
        return agent_response(
            "同步已执行，但有数据源失败：" + "；".join(public_sync_message(run.message) for run in failed),
            status="failed",
        ), 200
    return agent_response("同步完成：" + "；".join(run.message for run in runs), status="success"), 200


def cache_was_retained(message):
    return "仍保留" in (message or "") or "继续使用现有" in (message or "")


def public_sync_message(message):
    message = message or "外部数据源暂时无法连接。"
    for marker in ["网络原因：", "Network reason:", "原因："]:
        if marker in message:
            return message.split(marker, 1)[0].rstrip("；。") + "。"
    return message


def first_blocked_source(user, sources):
    threshold = timezone.now() - SYNC_COOLDOWN
    for source in sources:
        if SyncRun.objects.filter(source=source, triggered_by=user, started_at__gte=threshold).exists():
            return source
    return None


def execute_sync(source, user):
    handler = sync_handler(source)
    run = SyncRun.objects.create(source=source, status=SyncRun.Status.RUNNING, triggered_by=user)
    try:
        result = handler(force=True)
        run.status = {
            "updated": SyncRun.Status.SUCCESS,
            "skipped": SyncRun.Status.SKIPPED,
            "failed": SyncRun.Status.FAILED,
        }.get(result.status, SyncRun.Status.FAILED)
        run.updated_count = result.updated_count
        run.message = result.message
    except Exception as exc:
        run.status = SyncRun.Status.FAILED
        run.message = str(exc)
    run.finished_at = timezone.now()
    run.save(update_fields=["status", "updated_count", "message", "finished_at"])
    return run


def sync_handler(source):
    if source == SyncRun.Source.DOUBAN_CHART:
        return sync_douban_chart
    if source == SyncRun.Source.WEEKLY_REPUTATION:
        return sync_douban_weekly_reputation
    raise ValueError("Unknown sync source.")


def remember(request, user_message, assistant_message):
    history = request.session.get(HISTORY_KEY, [])
    history.append({"user": user_message, "assistant": assistant_message})
    request.session[HISTORY_KEY] = history[-6:]
    request.session.modified = True


def polish_with_glm(history, user_message, fallback_reply):
    api_key = getattr(settings, "ZHIPU_API_KEY", "")
    if not api_key:
        return fallback_reply
    try:
        return call_glm(history, user_message, fallback_reply)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return fallback_reply


def call_glm(history, user_message, fallback_reply):
    messages = [
        {
            "role": "system",
            "content": "你是电影资料馆博客的站内助手，只回答本博客、榜单、电影搜索和推荐流程相关问题。不要编造数据库里没有的数据。",
        }
    ]
    for item in history[-3:]:
        messages.append({"role": "user", "content": item["user"]})
        messages.append({"role": "assistant", "content": item["assistant"]})
    messages.append(
        {
            "role": "user",
            "content": f"用户问题：{user_message}\n站内工具结果：{fallback_reply}\n请用简洁中文回答。",
        }
    )
    payload = json.dumps(
        {
            "model": getattr(settings, "ZHIPU_MODEL", "glm-5.1"),
            "messages": messages,
            "temperature": 0.2,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        getattr(settings, "ZHIPU_API_URL", "https://open.bigmodel.cn/api/paas/v4/chat/completions"),
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.ZHIPU_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"] or fallback_reply
