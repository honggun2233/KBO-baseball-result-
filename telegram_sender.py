"""
Telegram Bot 메시지 전송 모듈
"""

import requests
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"


def send_message(
    text: str,
    chat_id: str = None,
    parse_mode: str = "Markdown",
) -> dict:
    """
    Telegram 채팅방에 메시지를 전송합니다.

    Args:
        text: 전송할 메시지 내용
        chat_id: 채팅방 ID (미지정 시 config의 기본값 사용)
        parse_mode: "Markdown" 또는 "HTML"

    Returns:
        Telegram API 응답 dict

    Raises:
        RuntimeError: 전송 실패 시
    """
    target_chat_id = chat_id or TELEGRAM_CHAT_ID

    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
    if not target_chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID가 설정되지 않았습니다.")

    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Telegram 전송 실패: {e}")

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API 오류: {result.get('description')}")

    return result


def test_connection() -> bool:
    """Bot 토큰이 유효한지 확인합니다."""
    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다.")
        return False

    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN, method="getMe")
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get("ok"):
            bot_name = data["result"].get("username")
            print(f"✅ Bot 연결 성공: @{bot_name}")
            return True
        else:
            print(f"❌ Bot 연결 실패: {data.get('description')}")
            return False
    except requests.RequestException as e:
        print(f"❌ 네트워크 오류: {e}")
        return False
