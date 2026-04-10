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
LAST_SENT_FILE = Path(__file__).parent / "last_sent_date.txt"


def _read_last_sent() -> date | None:
    """마지막으로 전송한 결과 날짜를 읽습니다."""
    try:
        return date.fromisoformat(LAST_SENT_FILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def _write_last_sent(d: date) -> None:
    LAST_SENT_FILE.write_text(d.isoformat(), encoding="utf-8")

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


def _all_cancelled(results: list) -> bool:
    """경기 결과가 전부 취소/연기이면 True."""
    if not results:
        return False
    return all(g.status in ("취소", "연기") for g in results)


def _all_not_started(results: list) -> bool:
    """경기 결과가 전부 '예정' 또는 비어있으면 True (취소 제외)."""
    if not results:
        return True
    return all(g.status == "예정" for g in results)


def send_today_results(target_date: date = None, force_date: bool = False) -> None:
    """KBO 결과 + 순위를 수집하여 Telegram으로 전송합니다.

    target_date 미지정 시 오늘 날짜를 사용하되,
    당일 경기가 전부 '예정' 상태이면 가장 최근 종료된 날 결과를 대신 전송합니다.
    force_date=True 이면 fallback 및 중복 체크 없이 지정 날짜 그대로 전송합니다.
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

    if not force_date:
        if _all_cancelled(results):
            # 전체 취소 → 취소 알림만 전송 (fallback 없음)
            log.info("당일(%s) 경기 전체 취소 → 취소 알림 전송", target_date.isoformat())
            last_sent = _read_last_sent()
            if last_sent == target_date:
                log.info("이미 %s 취소 알림을 전송했습니다. 건너뜀.", target_date.isoformat())
                return
            msg = format_results_message(results, target_date)
            log.info("전송할 메시지:\n%s", msg)
            try:
                send_message(msg)
                _write_last_sent(target_date)
                log.info("✅ Telegram 전송 완료")
            except RuntimeError as e:
                log.error("Telegram 전송 실패: %s", e)
            return

        elif _all_not_started(results):
            # 아직 시작 전 → 가장 최근 종료된 날 결과로 대체
            last_sent = _read_last_sent()
            for days_back in range(1, 8):
                fallback_date = target_date - timedelta(days=days_back)
                # last_sent 이하 날짜는 이미 전송(또는 취소 알림) 완료 → 더 이상 탐색 불필요
                if last_sent and fallback_date <= last_sent:
                    log.info(
                        "%s 이미 전송 완료된 날짜(%s) 이하 → fallback 중단",
                        fallback_date.isoformat(), last_sent.isoformat(),
                    )
                    return
                log.info(
                    "당일(%s) 경기 예정 상태 → %s 결과로 대체 시도",
                    target_date.isoformat(), fallback_date.isoformat(),
                )
                try:
                    fallback_results = get_kbo_results(fallback_date)
                except RuntimeError as e:
                    log.warning("%s 결과 수집 실패, 계속 탐색: %s", fallback_date.isoformat(), e)
                    continue
                if not _all_not_started(fallback_results) and not _all_cancelled(fallback_results):
                    results = fallback_results
                    target_date = fallback_date
                    break
            else:
                log.warning("최근 7일 내 종료된 경기를 찾지 못해 오늘 일정을 그대로 전송합니다.")

    # 중복 전송 방지: --date 지정이 아닐 때, 이미 같은 날 결과를 보냈으면 건너뜀
    if not force_date:
        last_sent = _read_last_sent()
        if last_sent == target_date:
            log.info("이미 %s 결과를 전송했습니다. 중복 전송 건너뜀.", target_date.isoformat())
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
        if not force_date:
            _write_last_sent(target_date)
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
