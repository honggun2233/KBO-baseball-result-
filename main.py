"""
KBO 야구 결과 Telegram 전송 - 메인 진입점

사용법:
  python main.py               # 스케줄러 실행 (매일 SEND_TIME에 자동 전송)
  python main.py --now         # 지금 즉시 오늘 결과 전송
  python main.py --date 2025-03-30  # 특정 날짜 결과 전송
  python main.py --test        # Bot 연결 테스트
"""

import argparse
import logging
import time
from datetime import date, datetime
from pathlib import Path

import schedule

from config import SEND_TIME
from kbo_scraper import get_kbo_results, format_results_message
from telegram_sender import send_message, test_connection

LOG_FILE = Path(__file__).parent / "kbo_bot.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


def send_today_results(target_date: date = None) -> None:
    """오늘(또는 지정 날짜) KBO 결과를 수집하여 Telegram으로 전송합니다."""
    if target_date is None:
        target_date = date.today()

    log.info("KBO 결과 수집 중... (%s)", target_date.isoformat())

    try:
        results = get_kbo_results(target_date)
    except RuntimeError as e:
        log.error("결과 수집 실패: %s", e)
        send_message(f"⚠️ KBO 결과 수집 실패\n{e}")
        return

    message = format_results_message(results, target_date)
    log.info("전송할 메시지:\n%s", message)

    try:
        send_message(message)
        log.info("✅ Telegram 전송 완료")
    except RuntimeError as e:
        log.error("Telegram 전송 실패: %s", e)


def run_scheduler() -> None:
    """매일 SEND_TIME에 경기 결과를 전송하는 스케줄러를 실행합니다."""
    log.info("스케줄러 시작 — 매일 %s KST 에 전송합니다.", SEND_TIME)

    schedule.every().day.at(SEND_TIME).do(send_today_results)

    log.info("다음 실행 예정: %s", schedule.next_run())

    while True:
        schedule.run_pending()
        time.sleep(30)


def main() -> None:
    parser = argparse.ArgumentParser(description="KBO 결과 Telegram 전송")
    parser.add_argument("--now", action="store_true", help="즉시 오늘 결과 전송")
    parser.add_argument("--date", metavar="YYYY-MM-DD", help="특정 날짜 결과 전송")
    parser.add_argument("--test", action="store_true", help="Telegram Bot 연결 테스트")
    args = parser.parse_args()

    if args.test:
        test_connection()
        return

    if args.date:
        try:
            target = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("날짜 형식 오류. 예: --date 2025-03-30")
            return
        send_today_results(target)
        return

    if args.now:
        send_today_results()
        return

    # 기본 동작: 스케줄러 실행
    run_scheduler()


if __name__ == "__main__":
    main()
