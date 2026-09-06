import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.agent.feishu import FeishuEventError, handle_feishu_event
from apps.agent.services import execute_pending_action, handle_message


def parse_json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return {}


@require_POST
def chat(request):
    data = parse_json_body(request)
    return JsonResponse(handle_message(request, data.get("message", "")))


@require_POST
def confirm_action(request):
    data = parse_json_body(request)
    response, status_code = execute_pending_action(request, data.get("action_id", ""))
    return JsonResponse(response, status=status_code)


@csrf_exempt
@require_POST
def feishu_events(request):
    data = parse_json_body(request)
    try:
        response, status_code = handle_feishu_event(
            data,
            headers=request.headers,
            raw_body=request.body.decode("utf-8"),
        )
    except FeishuEventError as exc:
        status_code = 403 if exc.status in {"invalid_token", "invalid_signature"} else 400
        response = {"status": exc.status, "message": exc.message}
    return JsonResponse(response, status=status_code)
