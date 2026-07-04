import httpx
import config

def send_telegram_message(message: str):
    """
    Sends a message to the specified Telegram chat using the Telegram Bot API.
    Gracefully skips sending if bot credentials are not configured.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[Telegram] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured. Skipping notification.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN.strip()}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID.strip(),
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = httpx.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print(f"[Telegram] Notification pushed successfully: \"{message[:40]}...\"")
    except Exception as e:
        print(f"[Telegram] Failed to send notification: {e}")
