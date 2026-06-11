"""
watcher.py — 학습 저장소를 감시하여 새 커밋마다 포트폴리오를 자동 생성합니다.

시작 시 처리되지 않은 HEAD 커밋이 있으면 자동으로 처리합니다.
(watcher가 꺼져 있는 동안 만든 커밋은 sync_commits.py로 일괄 처리하세요.)
"""
import os
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(__file__))
import portfolio_generator as pg


def get_current_hash(repo_path):
    try:
        from git import Repo
        return Repo(repo_path).head.commit.hexsha
    except Exception:
        return None


def main():
    study_repo = pg.STUDY_REPO_PATH
    print("=" * 56)
    print(f"감시 중: {study_repo}")
    print("=" * 56)
    print("새 커밋 감지 시 포트폴리오를 자동 생성합니다.")
    print("Ctrl+C로 중지\n")

    current_hash = get_current_hash(study_repo)
    if not current_hash:
        print(f"오류: '{study_repo}'에 접근할 수 없습니다.")
        print("경로가 올바른 Git 저장소인지 확인하세요.")
        return

    # 시작 시 HEAD가 아직 처리되지 않았으면 처리
    # (watcher가 꺼진 사이에 커밋이 생겼을 경우 자동 캐치)
    processed = pg.load_processed_commits()
    if current_hash not in processed:
        print(f"[미처리 커밋] {current_hash[:7]} — 포트폴리오 생성 중...")
        try:
            pg.process_commit(current_hash, skip_if_processed=True)
        except Exception as e:
            print(f"생성 오류: {e}")
            traceback.print_exc()
        print()

    last_hash = get_current_hash(study_repo)
    print(f"현재 HEAD: {last_hash[:7]}\n감시 중...\n")

    while True:
        try:
            time.sleep(2)
            new_hash = get_current_hash(study_repo)
            if new_hash and new_hash != last_hash:
                print(f"\n[새 커밋] {new_hash[:7]}")
                try:
                    pg.process_commit(new_hash, skip_if_processed=True)
                except Exception as e:
                    print(f"생성 오류: {e}")
                    traceback.print_exc()
                last_hash = new_hash
                print("\n감시 재개...\n")
        except KeyboardInterrupt:
            print("\n감시 종료.")
            break


if __name__ == "__main__":
    main()
