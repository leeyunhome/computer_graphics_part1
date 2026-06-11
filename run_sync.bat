@echo off
echo ================================================
echo  누락된 커밋 포트폴리오 일괄 생성
echo ================================================
echo.
echo watcher가 꺼져 있는 동안 만들어진 커밋들을 처리합니다.
echo.
echo 옵션:
echo   인수 없음  - 미처리 커밋만 생성
echo   --dry-run  - 처리 예정 목록만 출력 (실제 생성 안 함)
echo   --force    - 이미 처리된 커밋도 재생성
echo.

venv\Scripts\python.exe scripts\sync_commits.py %*
pause
