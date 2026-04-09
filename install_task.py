"""
Windows 작업 스케줄러에 KBO Bot 등록 (관리자 권한 불필요)

기존 VBS 시작 프로그램 방식(장기 실행 프로세스)과 달리,
매일 지정 시각에 --now 옵션으로 1회 실행하는 방식입니다.
→ 프로세스가 죽어도 다음 실행 시각에 자동으로 새로 시작됩니다.
"""

import sys
import io
import os
import subprocess
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).parent
MAIN_PY = SCRIPT_DIR / "main.py"
TASK_NAME = "KBO_Baseball_Bot"

# .env 에서 SEND_TIME 읽기 (없으면 23:00)
def _load_send_time() -> str:
    env_path = SCRIPT_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("SEND_TIME="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return "23:00"


def find_pythonw() -> str:
    for candidate in ["pythonw", "pythonw.exe"]:
        result = subprocess.run(["where", candidate], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0]
    return sys.executable


def install():
    send_time = _load_send_time()
    pythonw = find_pythonw()

    print(f"Python   : {pythonw}")
    print(f"스크립트  : {MAIN_PY}")
    print(f"실행 시각 : 매일 {send_time} KST")
    print()

    # 기존 작업 삭제 (오류 무시)
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True,
    )

    # 작업 등록: 매일 send_time 에 pythonw main.py --now 실행
    # /ru "" → 현재 로그인 사용자로 실행 (관리자 권한 불필요)
    cmd = [
        "schtasks", "/create",
        "/tn", TASK_NAME,
        "/tr", f'"{pythonw}" "{MAIN_PY}" --now',
        "/sc", "DAILY",
        "/st", send_time,
        "/f",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode == 0:
        print("✅ 작업 스케줄러 등록 완료!")
        print(f"   매일 {send_time} 에 자동으로 KBO 결과를 전송합니다.")
        print()
        print("확인 명령어:")
        print(f'  schtasks /query /tn "{TASK_NAME}"')
    else:
        print("❌ 등록 실패:", result.stderr.strip() or result.stdout.strip())
        print()
        print("힌트: 작업 스케줄러 등록에 실패하면 install_startup.py 를 대신 사용하세요.")


def uninstall():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode == 0:
        print("✅ 작업 스케줄러에서 제거됐습니다.")
    else:
        print("등록된 작업이 없거나 제거 실패:", result.stderr.strip())


def status():
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
        capture_output=True, text=True, encoding="utf-8",
    )
    if result.returncode == 0:
        print("✅ 작업 스케줄러 등록 상태:\n")
        print(result.stdout.strip())
    else:
        print("❌ 미등록 상태 (작업 없음)")

    log_path = SCRIPT_DIR / "kbo_bot.log"
    if log_path.exists():
        print("\n--- 최근 로그 (kbo_bot.log) ---")
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-10:]:
            print(line)
    else:
        print("\n로그 파일 없음 (아직 실행된 적 없음)")


def run_now():
    """즉시 오늘 결과 전송 (테스트용)"""
    pythonw = find_pythonw()
    print("결과 전송 중...")
    subprocess.run([pythonw, str(MAIN_PY), "--now"], cwd=str(SCRIPT_DIR))


if __name__ == "__main__":
    print("=" * 50)
    print("  KBO Bot — 작업 스케줄러 관리 (신뢰성 향상)")
    print("=" * 50)
    print("1. 등록  (매일 지정 시각 자동 실행)")
    print("2. 제거")
    print("3. 상태 확인")
    print("4. 지금 즉시 전송 (테스트)")
    choice = input("선택 (1/2/3/4): ").strip()

    if choice == "1":
        install()
    elif choice == "2":
        uninstall()
    elif choice == "3":
        status()
    elif choice == "4":
        run_now()
    else:
        print("잘못된 입력")
