#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


# Keep this validator focused on low-risk structural checks. Repository fit stays a human decision.
REQUIRED_BODY_SECTIONS = (
    "Section",
    "Why this belongs",
    "Primary documented web-agent use case",
    "Public reference",
    "Affiliation disclosure",
)

ALLOWED_SECTIONS = {
    "Autonomous Web Agents",
    "Computer-use Agents",
    "AI Web Automation Tools",
    "Dev Tools",
    "AI Web Scrapers/Crawlers",
    "Web Search & Query Tools",
    "Benchmarks & Research",
    "Tutorials & Guides",
    "Archive",
}

ITEM_LINE_RE = re.compile(r"^- \[(?P<name>[^\]]+)\]\((?P<url>https?://[^)]+)\) - (?P<rest>.+)$")


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def load_pull_request_event() -> dict | None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return None

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return event.get("pull_request")


def added_item_lines(base_sha: str) -> list[tuple[str, str]]:
    added: list[tuple[str, str]] = []
    for path in ("README.md", "ARCHIVE.md"):
        diff = run_git("diff", "--unified=0", f"{base_sha}...HEAD", "--", path)
        for line in diff.splitlines():
            if line.startswith("+++"):
                continue
            if re.match(r"^\+- \[", line):
                added.append((path, line[1:]))
    return added


def extract_body_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for heading in REQUIRED_BODY_SECTIONS:
        pattern = re.compile(
            rf"(?ms)^## {re.escape(heading)}\n+(.*?)(?=^## |\Z)"
        )
        match = pattern.search(body)
        if match:
            sections[heading] = match.group(1).strip()
    return sections


def normalize_markdown_line(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_section(value: str) -> str:
    value = re.sub(r"^[-*]\s*", "", value.strip(), flags=re.MULTILINE)
    first_line = value.splitlines()[0].strip()
    return first_line


def detect_section(path: str, item_line: str) -> str | None:
    if path == "ARCHIVE.md":
        return "Archive"

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    normalized_item_line = normalize_markdown_line(item_line)
    item_index = None
    for index, line in enumerate(lines):
        if normalize_markdown_line(line) == normalized_item_line:
            item_index = index
            break
    if item_index is None:
        return None

    for index in range(item_index - 1, -1, -1):
        line = lines[index]
        if line.startswith("### "):
            return line[4:].strip()
        if line.startswith("## "):
            return line[3:].strip()
    return None


def main() -> int:
    pull_request = load_pull_request_event()
    if not pull_request:
        print("No pull_request event detected. Skipping contribution validation.")
        return 0

    base_sha = pull_request["base"]["sha"]
    title = (pull_request.get("title") or "").strip()
    body = pull_request.get("body") or ""

    added_items = added_item_lines(base_sha)
    if not added_items:
        print("No new list item detected in README.md or ARCHIVE.md. Skipping contribution validation.")
        return 0

    errors: list[str] = []

    if len(added_items) != 1:
        errors.append("New item submissions must add exactly one list item per PR.")
        item_path = None
        item_line = None
    else:
        item_path, item_line = added_items[0]

    expected_prefix = "Add: "
    if len(added_items) == 1 and item_path == "ARCHIVE.md":
        expected_prefix = "Archive: "

    if not title.startswith(expected_prefix):
        errors.append(f'PR title must start with "{expected_prefix}" for this kind of submission.')

    sections = extract_body_sections(body)
    for heading in REQUIRED_BODY_SECTIONS:
        if not sections.get(heading):
            errors.append(f'PR body must include a non-empty "## {heading}" section.')

    declared_section = normalize_section(sections.get("Section", "")) if sections.get("Section") else ""
    if declared_section and declared_section not in ALLOWED_SECTIONS:
        errors.append("PR body section must match one of the repository section names exactly.")

    public_reference = sections.get("Public reference", "")
    if public_reference and not re.search(r"https?://", public_reference):
        errors.append('The "Public reference" section must include a public URL.')

    if len(added_items) == 1:
        match = ITEM_LINE_RE.match(item_line)
        if not match:
            errors.append("Added item line must follow the standard awesome-list format.")
        else:
            name = match.group("name").strip()
            url = match.group("url").strip()
            rest = match.group("rest").strip()
            description = re.sub(r"\s+!\[.*$", "", rest).strip()

            if not description or not description[0].isupper():
                errors.append("Item descriptions must begin with a capital letter.")
            if not description.endswith("."):
                errors.append("Item descriptions must end with a period.")

            actual_section = detect_section(item_path, item_line)
            if not actual_section:
                errors.append("Could not determine which section contains the added item.")
            elif declared_section and declared_section != actual_section:
                errors.append(
                    f'PR body says section "{declared_section}", but the item was added under "{actual_section}".'
                )

            repo_text = "\n".join(
                Path(path).read_text(encoding="utf-8") for path in ("README.md", "ARCHIVE.md") if Path(path).exists()
            )
            if repo_text.count(f"- [{name}](") > 1:
                errors.append(f'The item name "{name}" already exists in the repository list.')
            if repo_text.count(f"]({url})") > 1:
                errors.append(f'The URL "{url}" already exists in the repository list.')

    if errors:
        print("Contribution policy validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Contribution policy validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
