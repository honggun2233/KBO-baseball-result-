"""
Windows 시작 프로그램에 KBO Bot 등록 (관리자 권한 불필요)
로그인 시 자동으로 백그라운드 실행됩니다.
"""
import sys, io, os, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pathlib import Path

SCRIPT_DIR   = Path(__file__).parent
MAIN_PY      = SCRIPT_DIR / "main.py"
STARTUP_DIR  = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
VBS_PATH     = STARTUP_DIR / "KBO_Baseball_Bot.vbs"

# pythonw: 콘솔 창 없이 실행
def find_pythonw() -> str:
    for candidate in ["pythonw", "pythonw.exe"]:
        result = subprocess.run(["where", candidate], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().splitlines()[0]
    # 없으면 python으로 대체
    return sys.executable


def install():
    pythonw = find_pythonw()
    print(f"Python  : {pythonw}")
    print(f"스크립트 : {MAIN_PY}")
    print(f"등록 위치: {VBS_PATH}")
    print()

    # VBScript 생성 — 콘솔 창 없이 python 실행
    vbs_content = f'''Set oShell = CreateObject("WScript.Shell")
oShell.Run """{pythonw}"" ""{MAIN_PY}""", 0, False
'''
    VBS_PATH.write_text(vbs_content, encoding="utf-8")
    print("✅ 시작 프로그램 등록 완료!")
    print("   다음 Windows 로그인 시 자동으로 Bot이 실행됩니다.")
    print()

    ans = input("지금 바로 Bot을 시작할까요? (y/n): ").strip().lower()
    if ans == "y":
        subprocess.Popen([pythonw, str(MAIN_PY)],
                         cwd=str(SCRIPT_DIR),
                         creationflags=0x00000008)  # DETACHED_PROCESS
        print("✅ Bot 시작됨! (백그라운드 실행 중)")
        print(f"   로그 확인: {SCRIPT_DIR / 'kbo_bot.log'}")


def uninstall():
    if VBS_PATH.exists():
        VBS_PATH.unlink()
        print("✅ 시작 프로그램에서 제거됐습니다.")
    else:
        print("등록된 항목이 없습니다.")


def status():
    if VBS_PATH.exists():
        print("✅ 등록됨 —", VBS_PATH)
    else:
        print("❌ 미등록 상태")

    log_path = SCRIPT_DIR / "kbo_bot.log"
    if log_path.exists():
        print(f"\n--- 최근 로그 (kbo_bot.log) ---")
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in lines[-10:]:
            print(line)
    else:
        print("\n로그 파일 없음 (아직 실행된 적 없음)")


if __name__ == "__main__":
    print("=" * 45)
    print("  KBO Bot 시작 프로그램 관리")
    print("=" * 45)
    print("1. 등록 (로그인 시 자동 실행)")
    print("2. 제거")
    print("3. 상태 확인")
    choice = input("선택 (1/2/3): ").strip()

    if choice == "1":
        install()
    elif choice == "2":
        uninstall()
    elif choice == "3":
        status()
    else:
        print("잘못된 입력")
