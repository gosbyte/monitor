#!/usr/bin/env python3
"""Push commits to GitHub via REST API (blobs + trees + commits)."""
import os, sys, json, hashlib, base64, urllib.request, time

REPO_OWNER = "gosbyte"
REPO_NAME = "monitor"
BRANCH = "main"

TOKEN = os.environ.get("GH_PUSH_TOKEN", "")
if not TOKEN:
    print("ERROR: Set GH_PUSH_TOKEN environment variable")
    sys.exit(1)

WORK_DIR = "/opt/data/workspace/monitor-main-tmp"

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"token {TOKEN}")
    req.add_header("Accept", "application/vnd.github.v3+json")
    req.add_header("User-Agent", "hermes-agent")
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode()) if resp.status != 204 else {}
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:500]}")
        return None

def create_blob(content_bytes):
    data = {
        "content": base64.b64encode(content_bytes).decode(),
        "encoding": "base64"
    }
    result = api("POST", f"/repos/{REPO_OWNER}/{REPO_NAME}/git/blobs", data)
    if result:
        return result.get("sha")
    return None

def get_head_sha():
    ref = api("GET", f"/repos/{REPO_OWNER}/{REPO_NAME}/git/ref/heads/{BRANCH}")
    if ref:
        return ref["object"]["sha"]
    return None

def create_tree(blobs, base_tree_sha):
    tree_entries = []
    for filepath, blob_sha in blobs.items():
        tree_entries.append({
            "path": filepath,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha
        })
    data = {
        "tree": tree_entries,
        "base_tree": base_tree_sha
    }
    result = api("POST", f"/repos/{REPO_OWNER}/{REPO_NAME}/git/trees", data)
    if result:
        return result["sha"]
    return None

def create_commit(tree_sha, message, parent_sha):
    data = {
        "message": message,
        "tree": tree_sha,
        "parents": [parent_sha]
    }
    result = api("POST", f"/repos/{REPO_OWNER}/{REPO_NAME}/git/commits", data)
    if result:
        return result["sha"]
    return None

def update_ref(commit_sha):
    data = {
        "sha": commit_sha,
        "force": True
    }
    result = api("PATCH", f"/repos/{REPO_OWNER}/{REPO_NAME}/git/refs/heads/{BRANCH}", data)
    return result is not None

def main():
    print(f"Pushing to {REPO_OWNER}/{REPO_NAME}:{BRANCH}")
    
    # Get current HEAD
    head = get_head_sha()
    if not head:
        print("ERROR: Cannot get current HEAD")
        sys.exit(1)
    print(f"Base tree SHA: {head[:12]}")
    
    # Collect all tracked files
    blobs = {}
    count = 0
    
    for root, dirs, files in os.walk(WORK_DIR):
        rel = os.path.relpath(root, WORK_DIR)
        if rel in ('.git', '__pycache__', '.venv', 'data', 'htmlcov', '.pytest_cache'):
            continue
        if rel == '.':
            rel = ''
        
        for f in files:
            if f.endswith(('.pyc', '.pyo', '.swp', '.swo')):
                continue
            if f == 'app.py.bak':
                continue
            if f == 'rest_push.py':
                continue
                
            filepath = os.path.join(rel, f) if rel else f
            fullpath = os.path.join(WORK_DIR, filepath)
            
            try:
                with open(fullpath, 'rb') as fh:
                    content = fh.read()
                
                if len(content) > 10 * 1024 * 1024:
                    print(f"  SKIP (large): {filepath}")
                    continue
                
                blob_sha = create_blob(content)
                if blob_sha:
                    blobs[filepath] = blob_sha
                    count += 1
                else:
                    print(f"  FAIL: {filepath}")
                    
            except Exception as e:
                print(f"  ERROR {filepath}: {e}")
    
    print(f"\nPrepared {count} blobs")
    
    if count == 0:
        print("No files to push!")
        sys.exit(1)
    
    # Create tree
    print("Creating tree...")
    tree_sha = create_tree(blobs, head)
    if not tree_sha:
        print("ERROR: Failed to create tree")
        sys.exit(1)
    print(f"Tree SHA: {tree_sha[:12]}")
    
    # Create commit
    print("Creating commit...")
    commit_sha = create_commit(tree_sha, "feat: comprehensive optimization (19 improvements)", head)
    if not commit_sha:
        print("ERROR: Failed to create commit")
        sys.exit(1)
    print(f"Commit SHA: {commit_sha[:12]}")
    
    # Update ref
    print("Updating branch ref...")
    if update_ref(commit_sha):
        print(f"\n✅ Pushed successfully!")
        print(f"  https://github.com/{REPO_OWNER}/{REPO_NAME}/commit/{commit_sha}")
    else:
        print("ERROR: Failed to update ref")
        sys.exit(1)

if __name__ == "__main__":
    main()
