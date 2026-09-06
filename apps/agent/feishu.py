import base64
import hashlib
import json
import re
import urllib.error
import urllib.request

from django.conf import settings
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from apps.agent.services import answer_feishu_message, response_to_feishu_text


FEISHU_TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
FEISHU_REPLY_URL = "https://open.feishu.cn/open-apis/im/v1/messages/{message_id}/reply"


class FeishuEventError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


def handle_feishu_event(payload, headers=None, raw_body=""):
    verify_signature(headers or {}, raw_body)

    if "encrypt" in payload:
        payload = decrypt_payload(payload["encrypt"])

    if payload.get("type") == "url_verification":
        verify_token(payload.get("token"))
        return {"challenge": payload.get("challenge", "")}, 200

    verify_token(payload.get("header", {}).get("token") or payload.get("token"))
    if payload.get("header", {}).get("event_type") != "im.message.receive_v1":
        return {"status": "ignored"}, 200

    event = payload.get("event") or {}
    message = event.get("message") or {}
    message_id = message.get("message_id", "")
    text = extract_text_message(message)
    if not message_id or not text:
        return {"status": "ignored"}, 200

    response = answer_feishu_message(text)
    reply_to_feishu_message(message_id, response_to_feishu_text(response))
    return {"status": "ok"}, 200


def verify_token(token):
    expected = getattr(settings, "FEISHU_VERIFICATION_TOKEN", "")
    if expected and token != expected:
        raise FeishuEventError("invalid_token", "Invalid Feishu verification token.")


def verify_signature(headers, raw_body):
    signature = headers.get("X-Lark-Signature")
    if not signature:
        return
    timestamp = headers.get("X-Lark-Request-Timestamp", "")
    nonce = headers.get("X-Lark-Request-Nonce", "")
    encrypt_key = getattr(settings, "FEISHU_ENCRYPT_KEY", "")
    expected = hashlib.sha256(f"{timestamp}{nonce}{encrypt_key}{raw_body}".encode("utf-8")).hexdigest()
    if signature != expected:
        raise FeishuEventError("invalid_signature", "Invalid Feishu request signature.")


def decrypt_payload(encrypted_text):
    encrypt_key = getattr(settings, "FEISHU_ENCRYPT_KEY", "")
    if not encrypt_key:
        raise FeishuEventError("invalid_encryption", "Missing Feishu encrypt key.")
    try:
        raw = base64.b64decode(encrypted_text)
        iv = raw[:16]
        ciphertext = raw[16:]
        key = hashlib.sha256(encrypt_key.encode("utf-8")).digest()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()
        unpadder = PKCS7(128).unpadder()
        data = unpadder.update(padded) + unpadder.finalize()
        return json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise FeishuEventError("invalid_encryption", "Invalid Feishu encrypted payload.") from exc


def extract_text_message(message):
    if message.get("message_type") != "text":
        return ""
    try:
        content = json.loads(message.get("content") or "{}")
    except json.JSONDecodeError:
        return ""
    text = content.get("text", "")
    text = re.sub(r"<at\s+[^>]*>.*?</at>", "", text)
    return text.strip()


def reply_to_feishu_message(message_id, text):
    app_id = getattr(settings, "FEISHU_APP_ID", "")
    app_secret = getattr(settings, "FEISHU_APP_SECRET", "")
    if not app_id or not app_secret:
        return False

    token = get_tenant_access_token(app_id, app_secret)
    payload = json.dumps(
        {
            "msg_type": "text",
            "content": json.dumps({"text": text}, ensure_ascii=False),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        FEISHU_REPLY_URL.format(message_id=message_id),
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return False
    return data.get("code") == 0


def get_tenant_access_token(app_id, app_secret):
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode("utf-8")
    request = urllib.request.Request(
        FEISHU_TOKEN_URL,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    if data.get("code") != 0:
        raise FeishuEventError("token_error", data.get("msg") or "Failed to get tenant_access_token.")
    return data["tenant_access_token"]
