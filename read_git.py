from dulwich.repo import Repo
import datetime

repo_path = r"C:\Users\Admin\.gemini\antigravity\scratch\manga-ocr-extractor"
repo = Repo(repo_path)

print("Commit History:")
for i, walk_entry in enumerate(repo.get_walker()):
    commit = walk_entry.commit
    message = commit.message.decode('utf-8', 'replace').strip().split('\n')[0]
    time = datetime.datetime.fromtimestamp(commit.commit_time).strftime('%Y-%m-%d %H:%M:%S')
    print(f"{commit.id.decode('utf-8')} - {time} - {message}")
    if i >= 30:
        break
