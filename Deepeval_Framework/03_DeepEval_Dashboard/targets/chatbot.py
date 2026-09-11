"""Target runner configured for external/custom Chatbot endpoint."""
import os
import requests
from token_meter import token_meter

CHATBOT_URL = os.getenv("CHATBOT_URL", "https://aleeup.com/api/bots/NqLIxxNfaoPeChEFeF8nj/chat")
CHATBOT_CONVERSATION_ID = os.getenv("CHATBOT_CONVERSATION_ID", "HAZ40QTuYZs8l9wNSW7DK")
CHATBOT_VISITOR_ID = os.getenv("CHATBOT_VISITOR_ID", "i6a1en43eu")


def run_chatbot(message: str, history: list = None, provider: str = None, model: str = None, api_key: str = None) -> dict:
    url = CHATBOT_URL
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    }
    payload = {
        "message": message,
        "conversationId": CHATBOT_CONVERSATION_ID,
        "visitorId": CHATBOT_VISITOR_ID,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            raw_content = resp.text
            try:
                data = resp.json()
                if isinstance(data, dict):
                    reply_text = (
                        data.get("reply")
                        or data.get("answer")
                        or data.get("message")
                        or data.get("text")
                        or data.get("content")
                        or data.get("response")
                        or raw_content
                    )
                else:
                    reply_text = str(data)
            except Exception:
                data = raw_content
                reply_text = raw_content

            usage = {
                "prompt_tokens": max(5, len(message) // 4),
                "completion_tokens": max(5, len(reply_text) // 4),
            }
            token_meter.add_target_usage(usage)

            return {
                "reply": reply_text,
                "model": "external-chatbot-api",
                "mode": "live",
                "usage": usage,
                "raw": data,
            }
        else:
            raise ConnectionError(f"Chatbot endpoint HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        raise ConnectionError(f"Failed to connect to chatbot endpoint ({url}): {e}") from e
