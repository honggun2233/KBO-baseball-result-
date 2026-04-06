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
    game_id: str = ""          # 네이버 스포츠 game ID (미리보기 링크용)
    home_pitcher: str = ""     # 홈팀 선발 투수 (발표된 경우)
    away_pitcher: str = ""     # 원정팀 선발 투수 (발표된 경우)

    def is_finished(self) -> bool:
        return self.status == "종료"

    def preview_url(self) -> str:
        """네이버 스포츠 선발 투수 미리보기 링크"""
        if not self.game_id:
            return ""
        date_str = self.game_id[:8]
        return f"https://sports.naver.com/baseball/game/record?gameId={self.game_id}"

    def score_line(self) -> str:
        if self.home_score is not None and self.away_score is not None:
            return f"{self.away_score} - {self.home_score}"
        return "vs"

    def pitcher_line(self) -> str:
        """선발 투수 라인 (있을 때만)"""
        parts = []
        if self.away_pitcher:
            parts.append(f"{self.away_team} {self.away_pitcher}")
        if self.home_pitcher:
            parts.append(f"{self.home_team} {self.home_pitcher}")
        if parts:
            return "   🎯 " + " / ".join(parts)
        return ""

    def __str__(self) -> str:
        score = self.score_line()
        pitcher = self.pitcher_line()
        if self.is_finished():
            lines = [
                f"⚾ {self.away_team} {score} {self.home_team}",
                f"   📍 {self.stadium}",
            ]
            if pitcher:
                lines.append(pitcher)
            return "\n".join(lines)
        else:
            lines = [
                f"⚾ {self.away_team} vs {self.home_team}  [{self.status}]",
                f"   🕐 {self.start_time}  📍 {self.stadium}",
            ]
            if pitcher:
                lines.append(pitcher)
            return "\n".join(lines)


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

    last_error = None
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            break
        except requests.RequestException as e:
            last_error = e
            if attempt < 3:
                import time as _time
                _time.sleep(5 * attempt)
        except ValueError as e:
            raise RuntimeError(f"응답 JSON 파싱 실패: {e}")
    else:
        raise RuntimeError(f"네이버 스포츠 API 요청 실패 (3회 시도): {last_error}")

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
                    game_id=game.get("gameId", ""),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue

    return results


MY_TEAM = "LG"

WIN_COMMENTS = [
    "오늘도 LG 승리! 🔥",
    "엘지 이겼다! 최고야! 💙",
    "승리의 쌍둥이! 파이팅! 🏆",
]
LOSS_COMMENTS = [
    "오늘은 졌지만, 내일이 있다. 💙",
    "다음 경기엔 꼭 이기자! 힘내라 LG!",
    "아쉬운 패배... 내일을 믿어! 💙",
]
NO_GAME_COMMENT = "오늘 LG 경기가 없습니다."


def _lg_comment(game: "GameResult") -> str:
    """LG 경기 결과에 따른 한마디를 반환합니다."""
    lg_is_home = game.home_team == MY_TEAM
    if game.home_score is None or game.away_score is None:
        return ""
    lg_score = game.home_score if lg_is_home else game.away_score
    opp_score = game.away_score if lg_is_home else game.home_score

    import random
    if lg_score > opp_score:
        return random.choice(WIN_COMMENTS)
    elif lg_score < opp_score:
        return random.choice(LOSS_COMMENTS)
    else:
        return "무승부... 아쉽지만 선방했어! 💙"


def _lg_summary(game: "GameResult") -> str:
    """LG 경기 요약 블록을 반환합니다."""
    lg_is_home = game.home_team == MY_TEAM
    opponent = game.away_team if lg_is_home else game.home_team
    lg_score = game.home_score if lg_is_home else game.away_score
    opp_score = game.away_score if lg_is_home else game.home_score

    if lg_score is None or opp_score is None:
        return ""

    result_icon = "🔵 승" if lg_score > opp_score else ("🔴 패" if lg_score < opp_score else "⚪ 무")
    home_away = "홈" if lg_is_home else "원정"

    lines = [
        f"💙 *LG 트윈스 오늘의 경기* ({home_away})",
        f"   LG {lg_score} : {opp_score} {opponent}  {result_icon}",
        f"   📍 {game.stadium}",
        f"   _{_lg_comment(game)}_",
    ]
    return "\n".join(lines)


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

    # LG 경기 하이라이트 (종료된 경기 중에서)
    lg_game = next(
        (g for g in finished if MY_TEAM in (g.home_team, g.away_team)),
        None,
    )
    if lg_game:
        lines.append(_lg_summary(lg_game))
        lines.append("")

    if finished:
        lines.append("*[ 전체 경기 결과 ]*")
        for g in finished:
            # LG 경기는 강조 표시
            marker = " 👈" if MY_TEAM in (g.home_team, g.away_team) else ""
            lines.append(str(g) + marker)

    if others:
        if finished:
            lines.append("")
        lines.append("*[ 진행 / 예정 ]*")
        for g in others:
            marker = " 👈" if MY_TEAM in (g.home_team, g.away_team) else ""
            game_line = str(g) + marker
            # 예정 경기에 선발 투수 미리보기 링크 추가
            if g.status == "예정" and g.game_id:
                url = g.preview_url()
                game_line += f"\n   [🔍 선발 미리보기]({url})"
            lines.append(game_line)

    return header + "\n".join(lines)
