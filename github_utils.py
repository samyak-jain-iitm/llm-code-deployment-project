import os
import time
import requests
from github import Github
import logging

logger = logging.getLogger("github-utils")
GITHUB_API = "https://api.github.com"

def create_repo_and_push(token: str, repo_name: str, files: dict, owner: str = None) -> dict:
    """
    Create a public repository (owner uses token by default if owner not specified),
    create files via PyGithub create_file, and returns repo metadata.
    Returns: {"repo_url": ..., "commit_sha": ..., "owner": ...}
    """
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    gh = Github(token)
    if owner:
        user = gh.get_organization(owner) if is_org(gh, owner) else gh.get_user(owner)
    else:
        user = gh.get_user()

    # create repo
    repo = user.create_repo(name=repo_name, private=False, auto_init=False)
    logger.info("Created repo: %s", repo.full_name)

    last_commit_sha = None
    # create each file
    for path, content in files.items():
        # PyGithub create_file path should NOT start with a leading slash
        p = path.lstrip("/")
        try:
            res = repo.create_file(p, f"Add {p}", content)
            # res can be dict-like: it has 'commit' or results, try to fetch commit sha
            if hasattr(res, 'get'):
                commit = res.get('commit', None)
                if commit:
                    sha = getattr(commit, 'sha', None)
                    if sha:
                        last_commit_sha = sha
            else:
                # try attribute access
                commit = getattr(res, 'commit', None)
                if commit:
                    last_commit_sha = getattr(commit, 'sha', last_commit_sha)
            logger.info("Created file %s in %s", p, repo.full_name)
        except Exception as e:
            logger.exception("Error creating file %s: %s", p, e)
            raise

    # If no commit SHA found, get latest commit from default branch
    try:
        commits = repo.get_commits()
        last_commit_sha = commits[0].sha
    except Exception:
        last_commit_sha = last_commit_sha or ""

    return {"repo_url": repo.html_url, "commit_sha": last_commit_sha, "owner": user.login}


def update_repo_and_push(
    token: str,
    repo_name: str,
    files: dict,
    owner: str = None,
    round_num: int = 2,
) -> dict:
    """
    Update an existing repository with the files provided.
    All files, including README.md, will be fully replaced.

    Returns the same dict structure as create_repo_and_push:
    {"repo_url": <html_url>, "commit_sha": <latest_commit_sha>, "owner": <owner_login>}
    """
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required")

    gh = Github(token)

    # Determine owner
    owners_to_try = [owner] if owner else []
    env_owner = os.environ.get("GITHUB_OWNER")
    if env_owner and env_owner not in owners_to_try:
        owners_to_try.append(env_owner)
    try:
        token_user = gh.get_user().login
    except Exception:
        token_user = None
    if token_user and token_user not in owners_to_try:
        owners_to_try.append(token_user)

    # Find the repo
    repo = None
    for candidate in owners_to_try:
        try:
            if is_org(gh, candidate):
                repo = gh.get_organization(candidate).get_repo(repo_name)
            else:
                repo = gh.get_user(candidate).get_repo(repo_name)
            logger.info("Found existing repo %s/%s", candidate, repo_name)
            break
        except Exception:
            logger.debug("Repository %s not found for owner %s, trying next candidate", repo_name, candidate)

    if repo is None:
        raise RuntimeError(f"Repository {repo_name} not found under owners: {owners_to_try}")

    last_commit_sha = None

    # Update or create all files
    for path, content in files.items():
        p = path.lstrip("/")
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="ignore")

        try:
            existing = repo.get_contents(p)
            update_res = repo.update_file(p, f"Update {p} (round {round_num})", content, existing.sha)
            logger.info("Updated file %s in %s", p, repo.full_name)
        except Exception:
            update_res = repo.create_file(p, f"Add {p} (round {round_num})", content)
            logger.info("Created file %s in %s", p, repo.full_name)

        # Extract commit SHA
        if hasattr(update_res, "get"):
            commit = update_res.get("commit", None)
            if commit:
                last_commit_sha = getattr(commit, "sha", last_commit_sha)
        else:
            commit = getattr(update_res, "commit", None)
            if commit:
                last_commit_sha = getattr(commit, "sha", last_commit_sha)

    # Fallback: get latest commit SHA
    try:
        commits = repo.get_commits()
        last_commit_sha = commits[0].sha
    except Exception:
        last_commit_sha = last_commit_sha or ""

    return {"repo_url": repo.html_url, "commit_sha": last_commit_sha, "owner": repo.owner.login}


def get_repo_files(token: str, repo_name: str, owner: str = None) -> dict:
    """
    Returns a dict with the contents of index.html and README.md from the repo.
    Keys are filenames, values are file contents as strings.
    """
    gh = Github(token)

    # Determine owner
    if owner:
        if is_org(gh, owner):
            repo = gh.get_organization(owner).get_repo(repo_name)
        else:
            repo = gh.get_user(owner).get_repo(repo_name)
    else:
        repo = gh.get_user().get_repo(repo_name)

    files = {}
    for filename in ["index.html", "README.md"]:
        try:
            file_obj = repo.get_contents(filename)
            content = file_obj.decoded_content.decode("utf-8", errors="ignore")
            files[filename] = content
        except Exception:
            # File does not exist
            files[filename] = ""
    return files


def is_org(gh: Github, name: str) -> bool:
    try:
        gh.get_organization(name)
        return True
    except Exception:
        return False


def deploy_github_pages(owner: str, repo: str, token: str, round_num: int) -> dict:
    """
    Call the GitHub Pages API to configure a site:
    POST /repos/{owner}/{repo}/pages with {"source": {"branch":"main","path":"/"}}
    Requires repo scope or Pages write permission. See GitHub docs.
    """
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json"
    }
    if round_num == 1:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pages"
        payload = {"source": {"branch": "main", "path": "/"}}
        resp = requests.post(url, json=payload, headers=headers)
    else:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/pages/builds"
        resp = requests.post(url, headers=headers)

    if resp.status_code in (201, 202, 200):
        logger.info("Pages configuration set for %s/%s", owner, repo)
    else:
        logger.warning("Pages API response %s: %s", resp.status_code, resp.text)
    return resp.json() if resp.content else {}


def wait_for_pages_ready(pages_url: str, timeout_seconds: int = 120) -> bool:
    """
    Wait until pages_url returns HTTP 200 or timeout.
    """
    import requests
    start = time.time()
    while time.time() - start < timeout_seconds:
        try:
            r = requests.get(pages_url, timeout=5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def post_with_backoff(url: str, json_payload: dict, headers: dict = None, max_attempts: int = 6) -> bool:
    """
    POST and retry with exponential backoff (1,2,4,8...) seconds until success or attempts exhausted.
    Returns True on HTTP 200, False otherwise.
    """
    if headers is None:
        headers = {"Content-Type": "application/json"}
    attempt = 0
    delay = 1
    if url == "TESTING":
        return True
    else:
        while attempt < max_attempts:
            attempt += 1
            try:
                r = requests.post(url, json=json_payload, headers=headers, timeout=30)
                if r.status_code == 200:
                    logger.info("Evaluation server accepted payload on attempt %d", attempt)
                    return True
                else:
                    if url == "''":
                        logger.warning("Evaluation server returned %s (attempt %d): %s", r.status_code, attempt, r.text)
            except Exception as e:
                logger.warning("Error posting to evaluation_url (attempt %d): %s", attempt, e)

            time.sleep(delay)
            delay *= 2
        return False

def fetch_repo_files(token: str, owner: str, repo_name: str) -> dict:
    """
    Returns a dictionary of {filepath: content} for the default branch
    """
    gh = Github(token)
    repo = gh.get_repo(f"{owner}/{repo_name}")
    files = {}

    def _walk_dir(path=""):
        contents = repo.get_contents(path)
        for c in contents:
            if c.type == "dir":
                _walk_dir(c.path)
            elif c.type == "file":
                files[c.path] = c.decoded_content.decode("utf-8", errors="ignore")
    
    _walk_dir()
    return files