import os
import time
from git import Repo
import portfolio_generator

def get_latest_commit_hash(repo_path):
    try:
        repo = Repo(repo_path)
        return repo.head.commit.hexsha
    except Exception:
        return None

def main():
    study_repo = portfolio_generator.STUDY_REPO_PATH
    print(f"==================================================")
    print(f"👀 Watching for new commits in:")
    print(f"   {study_repo}")
    print(f"==================================================")
    print(f"Leave this window open. It will automatically update")
    print(f"your portfolio whenever you make a commit.")
    print(f"Press Ctrl+C to stop watching.\n")
    
    last_hash = get_latest_commit_hash(study_repo)
    if not last_hash:
        print("Warning: Could not read the study repository.")
        print(f"Please make sure '{study_repo}' is a valid Git repository.")
        return

    while True:
        try:
            time.sleep(2) # Check every 2 seconds
            current_hash = get_latest_commit_hash(study_repo)
            
            if current_hash and current_hash != last_hash:
                print(f"\n[!] New commit detected: {current_hash[:7]}")
                print("Triggering portfolio generation...")
                
                # Execute the portfolio generator
                try:
                    commit_msg, diff_text = portfolio_generator.get_latest_commit_diff(study_repo)
                    
                    if not diff_text.strip():
                        print("Notice: No significant code changes found in this commit.")
                    
                    content = portfolio_generator.generate_portfolio_post(commit_msg, diff_text)
                    
                    title = commit_msg.split('\n')[0]
                    first_line = content.split('\n')[0].strip()
                    if first_line.startswith('# '):
                        title = first_line[2:].strip()
                        
                    portfolio_generator.save_and_commit(title, content)
                    print("\n👀 Resuming watch...")
                    
                except Exception as e:
                    print(f"Error during generation: {e}")
                    
                # Update hash so we don't process it again
                last_hash = current_hash
                
        except KeyboardInterrupt:
            print("\nStopping watcher. Goodbye!")
            break

if __name__ == "__main__":
    main()
