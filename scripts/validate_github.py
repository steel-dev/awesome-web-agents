import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

README_PATH = Path("readme.md")
OUTPUT_PATH = Path("github-validation.json")
RAW_OUTPUT_PATH = Path("github-raw-results.json")
REPO_URL_RE = re.compile(r"https?://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")


def extract_repos_from_readme(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"README not found: {path}")

    text = path.read_text(encoding="utf-8")
    repos: set[str] = set()
    for match in REPO_URL_RE.finditer(text):
        owner = match.group(1)
        repo = match.group(2)
        repos.add(f"{owner}/{repo}")
    return sorted(repos)


def parse_github_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def github_api_get_repo(repo: str, token: str | None) -> tuple[int | None, dict, dict]:
    url = f"https://api.github.com/repos/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "awesome-web-agents-validator",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body) if body else {}
            return resp.status, data, dict(resp.headers.items())
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {"message": body[:200]}
        return exc.code, data, dict(exc.headers.items())
    except URLError as exc:
        return None, {"message": str(exc.reason)}, {}


def main() -> int:
    token = os.environ.get("GITHUB_TOKEN")
    repos = extract_repos_from_readme(README_PATH)
    results = {"healthy": [], "stale": [], "broken": [], "at_risk": []}
    raw_results: list[dict] = []

    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    rate_limit_reset_epoch: int | None = None

    for repo in repos:
        print(f"Checking {repo}...")

        if rate_limit_reset_epoch is not None:
            reset_dt = datetime.fromtimestamp(rate_limit_reset_epoch, tz=timezone.utc).isoformat()
            item = {
                "name": repo,
                "url": f"https://github.com/{repo}",
                "status": "at_risk",
                "reason": f"GitHub API rate limited until {reset_dt}",
            }
            results["at_risk"].append(item)
            raw_results.append(item)
            continue

        status_code, data, response_headers = github_api_get_repo(repo, token)
        url = f"https://github.com/{repo}"

        if status_code == 200:
            archived = bool(data.get("archived", False))
            stars = data.get("stargazers_count", 0)
            pushed_at = data.get("pushed_at")
            open_issues = data.get("open_issues_count", 0)
            description = (data.get("description") or "")[:100]
            last_commit = parse_github_datetime(pushed_at)

            item = {
                "name": repo,
                "url": url,
                "archived": archived,
                "stars": stars,
                "last_commit": pushed_at,
                "open_issues": open_issues,
                "description": description,
            }

            if archived:
                item["status"] = "stale"
                item["reason"] = "Repo is archived"
                results["stale"].append(item)
            elif last_commit and last_commit < one_year_ago:
                item["status"] = "stale"
                item["reason"] = f"No commits for over 1 year (last: {pushed_at[:10]})"
                results["stale"].append(item)
            else:
                item["status"] = "healthy"
                results["healthy"].append(item)

            raw_results.append(item)
            continue

        if status_code == 404:
            item = {
                "name": repo,
                "url": url,
                "status": "broken",
                "reason": "Repo not found or deleted",
            }
            results["broken"].append(item)
            raw_results.append(item)
            continue

        remaining = response_headers.get("X-RateLimit-Remaining")
        reset = response_headers.get("X-RateLimit-Reset")
        if status_code in (403, 429) and remaining == "0" and reset:
            try:
                rate_limit_reset_epoch = int(reset)
            except ValueError:
                rate_limit_reset_epoch = None
            reset_text = (
                datetime.fromtimestamp(rate_limit_reset_epoch, tz=timezone.utc).isoformat()
                if rate_limit_reset_epoch is not None
                else "unknown"
            )
            item = {
                "name": repo,
                "url": url,
                "status": "at_risk",
                "reason": f"GitHub API rate limit exceeded (resets at {reset_text})",
            }
            results["at_risk"].append(item)
            raw_results.append(item)
            continue

        message = data.get("message", "API error")
        item = {
            "name": repo,
            "url": url,
            "status": "at_risk",
            "reason": f"API error ({status_code}): {str(message)[:120]}",
        }
        results["at_risk"].append(item)
        raw_results.append(item)

    summary = {
        "total": len(repos),
        "healthy": len(results["healthy"]),
        "stale": len(results["stale"]),
        "broken": len(results["broken"]),
        "at_risk": len(results["at_risk"]),
    }
    results["summary"] = summary

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    RAW_OUTPUT_PATH.write_text(json.dumps(raw_results, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))

    if summary["at_risk"] > 0:
        print(
            "Hint: set GITHUB_TOKEN to avoid unauthenticated rate limits, e.g. "
            "GITHUB_TOKEN=$(gh auth token) python scripts/validate_github.py",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
