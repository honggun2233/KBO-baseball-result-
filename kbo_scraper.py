"""
KBO 야구 경기 결과 스크래퍼 (네이버 스포츠 API)
"""

import requests
from datetime import date, datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class GameResult:
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str          # "종료", "경기중", "예정", "취소" 등
    start_time: str
    stadium: str

    def is_finished(self) -> bool:
        return self.status == "종료"

    def score_line(self) -> str:
        if self.home_score is not None and self.away_score is not None:
            return f"{self.away_score} - {self.home_score}"
        return "vs"

    def __str__(self) -> str:
        score = self.score_line()
        if self.is_finished():
            return (
                f"⚾ {self.away_team} {score} {self.home_team}\n"
                f"   📍 {self.stadium}"
            )
        else:
            return (
                f"⚾ {self.away_team} vs {self.home_team}  [{self.status}]\n"
                f"   🕐 {self.start_time}  📍 {self.stadium}"
            )


# 팀 코드 → 한글 팀명 매핑
TEAM_NAME_MAP = {
    "HH": "한화",
    "HT": "KIA",
    "KT": "KT",
    "LG": "LG",
    "LT": "롯데",
    "NC": "NC",
    "OB": "두산",
    "SK": "SSG",
    "SS": "삼성",
    "WO": "키움",
}

# 상태 코드 → 한글 변환
# 실제 API 응답: BEFORE / LIVE / RESULT / CANCEL / POSTPONE / SUSPEND
STATUS_MAP = {
    "BEFORE": "예정",
    "LIVE": "경기중",
    "RESULT": "종료",   # 실제 API 종료 상태값
    "CANCEL": "취소",
    "POSTPONE": "연기",
    "SUSPEND": "중단",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://sports.naver.com/",
    "Accept": "application/json, text/plain, */*",
}


def get_kbo_results(game_date: date = None) -> list[GameResult]:
    """
    네이버 스포츠 API에서 KBO 경기 결과를 가져옵니다.
    game_date 미지정 시 오늘 날짜 사용.
    """
    if game_date is None:
        game_date = date.today()

    date_str = game_date.strftime("%Y-%m-%d")

    url = "https://api-gw.sports.naver.com/schedule/games"
    params = {
        "fields": "basic,schedule",
        "upperCategoryId": "kbaseball",
        "categoryId": "kbo",
        "fromDate": date_str,
        "toDate": date_str,
        "roundCode": "",
        "gameStatusCode": "",
    }

    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"네이버 스포츠 API 요청 실패: {e}")
    except ValueError as e:
        raise RuntimeError(f"응답 JSON 파싱 실패: {e}")

    return _parse_games(data)


def _parse_games(data: dict) -> list[GameResult]:
    results = []

    # 응답 구조: data["result"]["games"] 또는 data["games"]
    games_raw = (
        data.get("result", {}).get("games")
        or data.get("games")
        or []
    )

    for game in games_raw:
        try:
            # 팀명: API가 제공하는 이름 우선, 없으면 코드로 매핑
            home_team_code = game.get("homeTeamCode", "")
            away_team_code = game.get("awayTeamCode", "")
            home_team = (
                game.get("homeTeamName")
                or TEAM_NAME_MAP.get(home_team_code, home_team_code)
            )
            away_team = (
                game.get("awayTeamName")
                or TEAM_NAME_MAP.get(away_team_code, away_team_code)
            )

            # 실제 API 필드명: statusCode (gameStatusCode 아님)
            status_code = game.get("statusCode") or game.get("gameStatusCode", "BEFORE")

            home_score_raw = game.get("homeTeamScore")
            away_score_raw = game.get("awayTeamScore")
            home_score = int(home_score_raw) if home_score_raw is not None else None
            away_score = int(away_score_raw) if away_score_raw is not None else None

            # gameDateTime 형식: "2026-04-01T18:30:00" (타임존 없음)
            dt_raw = game.get("gameDateTime") or game.get("gameStartTime", "")
            if dt_raw and "T" in dt_raw:
                dt = datetime.fromisoformat(dt_raw[:19])  # 타임존 제거 후 파싱
                start_time = dt.strftime("%H:%M")
            else:
                start_time = dt_raw[:5] if len(dt_raw) >= 5 else dt_raw

            results.append(
                GameResult(
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    status=STATUS_MAP.get(status_code, status_code),
                    start_time=start_time,
                    stadium=game.get("stadium", ""),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue

    return results


def format_results_message(results: list[GameResult], game_date: date = None) -> str:
    """경기 결과 목록을 Telegram 메시지 문자열로 변환합니다."""
    if game_date is None:
        game_date = date.today()

    date_str = game_date.strftime("%Y년 %m월 %d일")
    header = f"⚾ *KBO 경기 결과* — {date_str}\n{'─' * 28}\n"

    if not results:
        return header + "\n경기 정보가 없습니다."

    finished = [g for g in results if g.is_finished()]
    others = [g for g in results if not g.is_finished()]

    lines = []

    if finished:
        lines.append("*[ 종료 ]*")
        for g in finished:
            lines.append(str(g))

    if others:
        if finished:
            lines.append("")
        lines.append("*[ 진행 / 예정 ]*")
        for g in others:
            lines.append(str(g))

    return header + "\n".join(lines)
