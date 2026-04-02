"""
초기 설정 도우미 스크립트
- Telegram Chat ID 자동 조회
- .env 파일 자동 생성
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import os
import requests
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def get_chat_id(token: str) -> str | None:
    """Bot에 메시지를 보낸 사용자의 Chat ID를 조회합니다."""
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ 네트워크 오류: {e}")
        return None

    if not data.get("ok"):
        print(f"❌ API 오류: {data.get('description')}")
        print("   → 토큰이 올바른지 확인하세요.")
        return None

    updates = data.get("result", [])
    if not updates:
        return None

    # 가장 최근 메시지의 chat id 반환
    latest = updates[-1]
    chat = (
        latest.get("message", {}).get("chat")
        or latest.get("channel_post", {}).get("chat")
        or {}
    )
    return str(chat.get("id", ""))


def write_env(token: str, chat_id: str, send_time: str = "23:00"):
    content = f"""TELEGRAM_BOT_TOKEN={token}
TELEGRAM_CHAT_ID={chat_id}
SEND_TIME={send_time}
"""
    ENV_PATH.write_text(content, encoding="utf-8")
    print(f"✅ .env 파일 저장 완료: {ENV_PATH}")


def main():
    print("=" * 50)
    print("  KBO Telegram Bot 초기 설정")
    print("=" * 50)

    # 1. 토큰 입력
    print("\n[1단계] BotFather에서 받은 토큰을 입력하세요.")
    print("  예) 7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    token = input("  토큰: ").strip()

    if not token or ":" not in token:
        print("❌ 올바른 토큰 형식이 아닙니다.")
        sys.exit(1)

    # 토큰 유효성 확인
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
    except Exception as e:
        print(f"❌ 네트워크 오류: {e}")
        sys.exit(1)

    if not data.get("ok"):
        print(f"❌ 토큰이 유효하지 않습니다: {data.get('description')}")
        sys.exit(1)

    bot_name = data["result"]["username"]
    print(f"✅ Bot 확인: @{bot_name}")

    # 2. Chat ID 조회
    print(f"\n[2단계] Telegram에서 @{bot_name} 에게 아무 메시지나 보내세요.")
    input("  메시지를 보낸 후 Enter를 누르세요...")

    chat_id = get_chat_id(token)

    if not chat_id:
        print("❌ Chat ID를 찾지 못했습니다.")
        print("   → Bot에게 메시지를 보냈는지 확인 후 다시 시도하세요.")
        sys.exit(1)

    print(f"✅ Chat ID 확인: {chat_id}")

    # 3. 전송 시각 설정
    print("\n[3단계] 매일 결과를 전송할 시각을 입력하세요.")
    print("  기본값: 23:00 (엔터만 누르면 기본값 사용)")
    send_time_input = input("  시각 (HH:MM): ").strip()
    send_time = send_time_input if send_time_input else "23:00"

    # 4. .env 저장
    write_env(token, chat_id, send_time)

    # 5. 테스트 전송
    print("\n[4단계] 테스트 메시지를 전송할까요? (y/n)")
    if input("  선택: ").strip().lower() == "y":
        test_url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "✅ KBO Telegram Bot 설정 완료!\n매일 경기 결과를 이 채팅으로 전송합니다.",
        }
        try:
            r = requests.post(test_url, json=payload, timeout=10)
            if r.json().get("ok"):
                print("✅ 테스트 메시지 전송 성공!")
            else:
                print(f"❌ 전송 실패: {r.json().get('description')}")
        except Exception as e:
            print(f"❌ 오류: {e}")

    print("\n설정 완료! 다음 명령어로 바로 실행할 수 있습니다:")
    print("  python main.py --now       # 오늘 결과 즉시 전송")
    print("  python main.py             # 스케줄러 시작")


if __name__ == "__main__":
    main()
