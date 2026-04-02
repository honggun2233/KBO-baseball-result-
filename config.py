"""
환경 변수 로드 및 설정
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Telegram 설정
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# 스케줄러 설정
# 매일 이 시각에 오늘 경기 결과를 전송합니다 (KST 기준, 24시간 형식)
SEND_TIME: str = os.getenv("SEND_TIME", "23:00")
