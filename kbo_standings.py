"""
KBO 팀 순위 스크래퍼 (KBO 공식 홈페이지 API)
"""

import re
import requests
from dataclasses import dataclass


@dataclass
class TeamStanding:
    rank: int
    team: str
    games: int
    wins: int
    losses: int
    draws: int
    win_pct: str
    game_behind: str
    recent: str      # 최근 흐름 예: "1승", "2패"

    def is_lg(self) -> bool:
        return self.team == "LG"


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.koreabaseball.com/",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


def get_standings() -> list[TeamStanding]:
    """KBO 공식 홈페이지에서 현재 팀 순위를 가져옵니다."""
    url = "https://www.koreabaseball.com/ws/Main.asmx/GetTeamRank"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        raise RuntimeError(f"KBO 순위 API 요청 실패: {e}")
    except ValueError as e:
        raise RuntimeError(f"순위 응답 JSON 파싱 실패: {e}")

    standings = []
    for row_obj in data.get("rows", []):
        cells = [_strip_tags(c["Text"]) for c in row_obj["row"]]
        if len(cells) < 9:
            continue
        try:
            standings.append(TeamStanding(
                rank=int(cells[0]),
                team=cells[1],
                games=int(cells[2]),
                wins=int(cells[3]),
                losses=int(cells[4]),
                draws=int(cells[5]),
                win_pct=cells[6],
                game_behind=cells[7],
                recent=cells[8],
            ))
        except (ValueError, IndexError):
            continue

    return standings


def format_standings_message(standings: list[TeamStanding]) -> str:
    """순위표를 Telegram 메시지 형식으로 변환합니다."""
    if not standings:
        return "순위 정보를 불러오지 못했습니다."

    lines = ["*[ KBO 팀 순위 ]*", "```"]
    lines.append(f"{'순위':<3} {'팀':<5} {'경기':>3} {'승':>3} {'패':>3} {'승률':>6} {'최근'}")
    lines.append("─" * 34)

    for s in standings:
        marker = "◀" if s.is_lg() else "  "
        lines.append(
            f"{s.rank:<3} {s.team:<5} {s.games:>3} {s.wins:>3} {s.losses:>3} "
            f"{s.win_pct:>6} {s.recent:<4}{marker}"
        )

    lines.append("```")
    return "\n".join(lines)
