"""
KBO 선발 투수 정보 수집 모듈

KBO 공식 홈페이지의 GetScheduleList API는 선발 투수 이름을 직접 제공하지 않습니다.
(모든 선발 투수 데이터는 JavaScript 렌더링 또는 인증 필요)

현재 구현:
  - KBO GetScheduleList API로 경기별 game_id 수집
  - game_id 기반으로 Naver Sports 미리보기 URL 생성
  - 향후 공개 API가 생기면 이 모듈에서 업데이트

반환 형식: {game_id: {"home": 홈투수명, "away": 원정투수명}}
"""

import re
import requests
from datetime import date

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.koreabaseball.com/Schedule/Schedule.aspx",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://www.koreabaseball.com",
}

_TAG_RE = re.compile(r"<[^>]+>")
_GAME_ID_RE = re.compile(r"gameId=(\w{15,})")  # 예: 20260407LGNC02026


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://www.koreabaseball.com/", timeout=10)
    session.get("https://www.koreabaseball.com/Schedule/Schedule.aspx", timeout=10)
    return session


def get_game_ids_for_date(game_date: date) -> dict[str, str]:
    """
    KBO GetScheduleList에서 해당 날짜의 경기 ID를 추출합니다.
    반환: {"LGNC": "20260407LGNC02026", ...} (away+home 코드 → 전체 game_id)
    """
    try:
        session = _get_session()
        r = session.post(
            "https://www.koreabaseball.com/ws/Schedule.asmx/GetScheduleList",
            data={
                "leId": "1",
                "srIdList": "0,9,6",
                "seasonId": str(game_date.year),
                "gameMonth": game_date.strftime("%m"),
                "teamId": "",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception:
        return {}

    day_str = game_date.strftime("%m.%d")  # 예: "04.07"
    game_ids: dict[str, str] = {}
    current_date_matches = False

    for row_obj in data.get("rows", []):
        cells = row_obj.get("row", [])
        if not cells:
            continue

        raw_date = _TAG_RE.sub("", cells[0].get("Text", "")).strip()
        if raw_date:
            current_date_matches = day_str in raw_date

        if not current_date_matches:
            continue

        # relay 셀(index 3)의 href에서 gameId 추출
        relay_html = cells[3].get("Text", "") if len(cells) > 3 else ""
        m = _GAME_ID_RE.search(relay_html)
        if m:
            full_id = m.group(1)
            # 팀 코드 키 (7~10번째 문자): 예 "LGNC"
            key = full_id[8:12]
            game_ids[key] = full_id

    return game_ids


def build_pitcher_preview_urls(game_date: date) -> dict[str, str]:
    """
    각 경기의 네이버 스포츠 미리보기 URL을 반환합니다.
    반환: {game_id: naver_preview_url}
    """
    game_ids = get_game_ids_for_date(game_date)
    return {
        gid: f"https://sports.naver.com/baseball/game/record?gameId={gid}"
        for gid in game_ids.values()
    }
