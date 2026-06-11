"""
sync_commits.py — 학습 저장소의 누락된 커밋에 대해 포트폴리오를 일괄 생성합니다.

watcher.py가 꺼져 있는 동안 만들어진 커밋들을 소급 처리할 때 사용하세요.
커밋은 오래된 순서(chronological)로 처리됩니다.

사용법:
  venv\\Scripts\\python.exe scripts\\sync_commits.py           # 미처리 커밋만
  venv\\Scripts\\python.exe scripts\\sync_commits.py --force   # 전체 재생성
  venv\\Scripts\\python.exe scripts\\sync_commits.py --dry-run # 처리 예정 목록만 출력
"""
import os
import sys
import argparse
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import portfolio_generator as pg
from git import Repo


def main():
    parser = argparse.ArgumentParser(description="누락된 커밋 포트폴리오 일괄 생성")
    parser.add_argument('--force', action='store_true', help='이미 처리된 커밋도 재생성')
    parser.add_argument('--dry-run', action='store_true', help='목록만 출력 (실제 생성 안 함)')
    args = parser.parse_args()

    print("=" * 60)
    print("학습 저장소 커밋 동기화")
    print("=" * 60)

    try:
        repo = Repo(pg.STUDY_REPO_PATH)
    except Exception as e:
        print(f"오류: 학습 저장소를 열 수 없습니다.\n  경로: {pg.STUDY_REPO_PATH}\n  {e}")
        sys.exit(1)

    processed = pg.load_processed_commits()

    # 모든 커밋을 오래된 순서로 (oldest first)
    all_commits = list(reversed(list(repo.iter_commits('HEAD'))))

    if args.force:
        pending = all_commits
    else:
        pending = [c for c in all_commits if c.hexsha not in processed]

    print(f"전체 커밋:    {len(all_commits)}개")
    print(f"처리 완료:    {len(processed)}개")
    print(f"처리 예정:    {len(pending)}개\n")

    if not pending:
        print("모든 커밋이 이미 처리되었습니다.")
        return

    for i, commit in enumerate(pending, 1):
        short = commit.hexsha[:7]
        msg = commit.message.strip().split('\n')[0][:60]
        print(f"[{i}/{len(pending)}] {short} — {msg}")

        if args.dry_run:
            continue

        try:
            pg.process_commit(commit.hexsha, skip_if_processed=not args.force)
        except Exception as e:
            print(f"  오류 (건너뜀): {e}")
            traceback.print_exc()
        print()

    if not args.dry_run:
        print(f"\n완료: {len(pending)}개 커밋 처리됨.")
    else:
        print(f"\n(dry-run) 실제로 생성하려면 --dry-run 없이 실행하세요.")


if __name__ == "__main__":
    main()
