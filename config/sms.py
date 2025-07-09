import requests

TELEGRAM_BOT_TOKEN = "8034634515:AAGcI4TGLiQIjEbDBZWFfgp4Ld_SunKP7zM"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

def send_telegram_code(chat_id: str, code: str) -> bool:
    message = f"🔐 Код подтверждения: {code}"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(TELEGRAM_API_URL, data=payload)
        if response.status_code != 200:
            print(f"[Telegram Error] Status: {response.status_code}, Text: {response.text}")
            return False
        return True
    except Exception as e:
        print(f"[Telegram Exception] {e}")
        return False
