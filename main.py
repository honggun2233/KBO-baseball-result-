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
from datetime import date, datetime, timedelta
from pathlib import Path

import schedule

from config import SEND_TIME
from kbo_scraper import get_kbo_results, format_results_message
from kbo_standings import get_standings, format_standings_message
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


def _all_not_started(results: list) -> bool:
    """경기 결과가 전부 '예정' 또는 비어있으면 True."""
    if not results:
        return True
    return all(not g.is_finished() and g.status == "예정" for g in results)


def send_today_results(target_date: date = None, force_date: bool = False) -> None:
    """KBO 결과 + 순위를 수집하여 Telegram으로 전송합니다.

    target_date 미지정 시 오늘 날짜를 사용하되,
    당일 경기가 전부 '예정' 상태이면 전날 결과를 대신 전송합니다.
    force_date=True 이면 fallback 없이 지정 날짜 그대로 전송합니다.
    """
    if target_date is None:
        target_date = date.today()

    log.info("KBO 결과 수집 중... (%s)", target_date.isoformat())

    # 경기 결과 수집
    try:
        results = get_kbo_results(target_date)
    except RuntimeError as e:
        log.error("결과 수집 실패: %s", e)
        send_message(f"⚠️ KBO 결과 수집 실패\n{e}")
        return

    # 당일 경기가 전부 예정(아직 시작 전)이면 전날 결과로 대체
    # (명시적으로 날짜를 지정한 경우엔 fallback 하지 않음)
    if not force_date and _all_not_started(results):
        fallback_date = target_date - timedelta(days=1)
        log.info(
            "당일(%s) 경기가 아직 예정 상태 → 전날(%s) 결과로 대체",
            target_date.isoformat(), fallback_date.isoformat(),
        )
        try:
            results = get_kbo_results(fallback_date)
            target_date = fallback_date
        except RuntimeError as e:
            log.error("전날 결과 수집도 실패: %s", e)
            send_message(f"⚠️ KBO 결과 수집 실패\n{e}")
            return

    # 순위 수집
    try:
        standings = get_standings()
    except RuntimeError as e:
        log.warning("순위 수집 실패 (결과만 전송): %s", e)
        standings = []

    results_msg = format_results_message(results, target_date)
    log.info("전송할 메시지:\n%s", results_msg)

    try:
        send_message(results_msg)
        if standings:
            send_message(format_standings_message(standings))
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
        send_today_results(target, force_date=True)
        return

    if args.now:
        send_today_results()
        return

    # 기본 동작: 스케줄러 실행
    run_scheduler()


if __name__ == "__main__":
    main()
