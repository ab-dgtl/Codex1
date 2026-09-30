import logging
import time

import httpx

from .config import Settings
from .db import enqueue, list_runs


def command(text, path):
    if text.startswith("/run "):
        question = text[5:].strip()
        if not 3 <= len(question) <= 2000:
            return "Question must contain 3–2000 characters."
        return "Queued: " + enqueue(path, {"question": question, "provider": "demo", "analyze": False})
    if text == "/runs":
        rows = list_runs(path)[:10]
        return "\n".join(f"{r['id']} {r['status']} {r['result']}" for r in rows)[:4000] or "No runs."
    return "/run <question> — demo experiment\n/runs — recent results"


def main():
    settings = Settings()
    allowed = {int(x.strip()) for x in settings.telegram_allowed_user_ids.split(",") if x.strip()}
    if not settings.telegram_bot_token or not allowed:
        raise SystemExit("Configure Telegram token and allowed user IDs first")
    base = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
    offset = 0
    with httpx.Client(timeout=40) as client:
        while True:
            try:
                response = client.get(base + "/getUpdates", params={"offset": offset, "timeout": 25})
                response.raise_for_status()
                body = response.json()
                if not body.get("ok"):
                    raise ValueError("Telegram rejected polling")
                for update in body["result"]:
                    offset = update["update_id"] + 1
                    msg = update.get("message", {})
                    if msg.get("from", {}).get("id") not in allowed or msg.get("chat", {}).get("type") != "private":
                        continue
                    reply = command(msg.get("text", ""), settings.database_path)
                    sent = client.post(base + "/sendMessage", json={"chat_id": msg["chat"]["id"], "text": reply})
                    sent.raise_for_status()
            except (httpx.HTTPError, ValueError):
                logging.warning("Telegram request failed; retrying without logging credentials")
                time.sleep(5)


if __name__ == "__main__":
    main()
