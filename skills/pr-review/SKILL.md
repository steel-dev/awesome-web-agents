---
name: awesome-web-agents-pr-review
description: Review pull requests for the awesome-web-agents repository. Use when asked to validate a PR, assess whether a submission fits the repo, inspect README or ARCHIVE additions, check merge readiness, or apply the repository's web-agent-first contribution policy to a GitHub pull request.
---

# Awesome Web Agents PR Review

## Overview

Review PRs in this repository by applying the local policy and checking the changed files. Treat `contributing.md` as the source of truth for acceptance criteria.

## Read First

- `contributing.md`
- `readme.md`
- `ARCHIVE.md` when the change might belong in the archive
- `scripts/validate_contribution.py` when you need structural validation details

Do not restate repo policy from memory when those files are available. Quote or summarize the repository's own rules instead.

## Workflow

### 1. Inspect the PR

Use `gh` first:

- `gh pr view <number> --repo steel-dev/awesome-web-agents --json title,number,state,isDraft,author,baseRefName,headRefName,files,additions,deletions,mergeable,mergeStateStatus,labels,url,body`
- `gh pr diff <number> --repo steel-dev/awesome-web-agents --patch`
- `gh pr checks <number> --repo steel-dev/awesome-web-agents`

If you need the exact branch locally, fetch it with:

- `git fetch origin refs/pull/<number>/head:pr-<number>`

### 2. Apply local policy

Use `contributing.md` for the actual acceptance rubric. Use `readme.md` and `ARCHIVE.md` only to judge section fit, duplicates, and whether a project belongs in the main list or archive.

### 3. Run structural validation when useful

When reviewing a local branch or checking CI behavior, run:

- `python3 scripts/validate_contribution.py`

Treat the script as a structural check, not the decision-maker. Human review still decides repository fit.

### 4. Produce the review

Use a code-review mindset:

- Present findings first, ordered by severity, with file references when applicable.
- If there are no findings, say that explicitly.
- After findings, give one clear decision: `Accept`, `Request changes`, or `Close`.
- Separate policy fit from technical mergeability. A PR can be mergeable in GitHub and still fail repository scope.

## Output Shape

Keep the final review compact:

- one sentence on PR state or scope if useful
- findings first
- verdict second
- short rationale last
