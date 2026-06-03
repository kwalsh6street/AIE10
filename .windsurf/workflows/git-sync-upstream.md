---
description: Set up upstream remote and sync course materials from the AI Maker Space repository
---

1. Inspect the repository state:
```bash
git rev-parse --show-toplevel
git status --short --branch
git remote -v
git branch --show-current
```

2. If `upstream` is missing, add it (confirm the URL with the user first):
```bash
git remote add upstream <upstream-url>
git remote -v
```

3. Check for local changes before pulling. If the worktree is dirty, stop and ask the user to commit or stash before continuing.

4. Pull the latest changes from upstream:
```bash
git pull upstream main --allow-unrelated-histories
```

5. Confirm the result:
```bash
git status --short --branch
```

6. If the user wants to push their work to their remote:
```bash
git push origin main
```
