import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

README_PATH = Path("readme.md")
OUTPUT_PATH = Path("web-validation.json")

MD_LINK_RE = re.compile(r'(!?)\[([^\]]+)\]\((https?://[^)\s]+)\)')
HREF_RE = re.compile(r'href=["\'](https?://[^"\']+)["\']')
H2_RE = re.compile(r"^##\s+(.+)$")
H3_RE = re.compile(r"^###\s+(.+)$")


def strip_html_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def extract_links_from_readme(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"README not found: {path}")

    content = strip_html_comments(path.read_text(encoding="utf-8"))
    links_by_url: dict[str, dict] = {}
    current_h2 = "Uncategorized"
    current_h3 = ""

    for line_no, line in enumerate(content.splitlines(), start=1):
        h2_match = H2_RE.match(line.strip())
        if h2_match:
            current_h2 = h2_match.group(1).strip()
            current_h3 = ""
            continue

        h3_match = H3_RE.match(line.strip())
        if h3_match:
            current_h3 = h3_match.group(1).strip()
            continue

        section = f"{current_h2} / {current_h3}" if current_h3 else current_h2

        for match in MD_LINK_RE.finditer(line):
            is_image = match.group(1) == "!"
            label = match.group(2).strip()
            url = match.group(3).strip()
            if is_image:
                continue
            links_by_url.setdefault(
                url,
                {
                    "name": label,
                    "url": url,
                    "section": section,
                    "line": line_no,
                    "source": "markdown",
                },
            )

        for match in HREF_RE.finditer(line):
            url = match.group(1).strip()
            links_by_url.setdefault(
                url,
                {
                    "name": url,
                    "url": url,
                    "section": section,
                    "line": line_no,
                    "source": "html",
                },
            )

    return list(links_by_url.values())


def check_url(url: str, timeout_seconds: int = 12) -> tuple[str, str, str]:
    # Follow redirects and report final status/effective URL.
    result = subprocess.run(
        [
            "curl",
            "-sS",
            "-o",
            "/dev/null",
            "-w",
            "%{http_code}||%{url_effective}||%{redirect_url}",
            "-L",
            "--max-time",
            str(timeout_seconds),
            url,
        ],
        capture_output=True,
        text=True,
        timeout=timeout_seconds + 5,
    )
    output = result.stdout.strip()
    parts = output.split("||")
    status_code = parts[0] if len(parts) > 0 else "000"
    final_url = parts[1] if len(parts) > 1 and parts[1] else url
    redirect_url = parts[2] if len(parts) > 2 else ""
    return status_code, final_url, redirect_url


def main() -> int:
    links = extract_links_from_readme(README_PATH)
    results = {"healthy": [], "redirects": [], "broken": [], "at_risk": []}

    for item in links:
        name = item["name"]
        url = item["url"]
        section = item["section"]
        line_no = item["line"]
        print(f"Checking {name}...")

        try:
            status_code, final_url, redirect_url = check_url(url)

            base_entry = {
                "name": name,
                "url": url,
                "final_url": final_url,
                "section": section,
                "line": line_no,
            }

            if status_code.startswith("2"):
                if final_url != url:
                    results["redirects"].append(
                        {
                            **base_entry,
                            "status": "redirect",
                            "status_code": int(status_code),
                            "redirect_url": redirect_url or final_url,
                        }
                    )
                else:
                    results["healthy"].append(
                        {
                            **base_entry,
                            "status": "healthy",
                            "status_code": int(status_code),
                        }
                    )
            elif status_code.startswith("3"):
                results["redirects"].append(
                    {
                        **base_entry,
                        "status": "redirect",
                        "status_code": int(status_code),
                        "redirect_url": redirect_url or final_url,
                    }
                )
            elif status_code in {"404", "410"}:
                results["broken"].append(
                    {
                        **base_entry,
                        "status": "broken",
                        "status_code": int(status_code),
                        "reason": f"HTTP {status_code}",
                    }
                )
            elif status_code == "000":
                results["broken"].append(
                    {
                        **base_entry,
                        "status": "broken",
                        "reason": "Connection failed or timeout",
                    }
                )
            else:
                results["at_risk"].append(
                    {
                        **base_entry,
                        "status": "at_risk",
                        "status_code": int(status_code),
                        "reason": f"HTTP {status_code}",
                    }
                )
        except subprocess.TimeoutExpired:
            results["at_risk"].append(
                {
                    "name": name,
                    "url": url,
                    "section": section,
                    "line": line_no,
                    "status": "at_risk",
                    "reason": "Timeout",
                }
            )
        except Exception as exc:
            results["at_risk"].append(
                {
                    "name": name,
                    "url": url,
                    "section": section,
                    "line": line_no,
                    "status": "at_risk",
                    "reason": str(exc)[:120],
                }
            )

    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(links),
        "healthy": len(results["healthy"]),
        "redirects": len(results["redirects"]),
        "broken": len(results["broken"]),
        "at_risk": len(results["at_risk"]),
    }
    results["summary"] = summary

    OUTPUT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
