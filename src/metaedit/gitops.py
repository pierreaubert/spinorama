from __future__ import annotations

from typing import Tuple, Optional

import datetime as _dt
import os
import re
import shutil
import subprocess


def _run(cmd: list[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def sanitize_ref(text: str) -> str:
    # Lowercase, replace non-alnum with '-', collapse dashes, trim
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "meta"


def today_str() -> str:
    return _dt.date.today().isoformat()


def plan_pr_actions(
    *,
    current_branch: str,
    up_to_date: bool,
    files: list[str],
    speaker_key: str,
    date_str: str,
    gh_available: bool,
) -> list[list[str]]:
    if current_branch != "develop":
        raise ValueError("Repository is not on 'develop' branch")
    if not up_to_date:
        raise ValueError("Local 'develop' is not up-to-date with 'origin/develop'")
    branch = f"metadata-{sanitize_ref(speaker_key)}-{date_str}"
    title = f"metadata-{speaker_key}-{date_str}"

    cmds: list[list[str]] = []
    cmds.append(["git", "switch", "-c", branch])
    if files:
        cmds.append(["git", "add", *files])
    cmds.append(["git", "commit", "-m", f"metadata: {speaker_key}"])
    cmds.append(["git", "push", "-u", "origin", branch])
    if gh_available:
        cmds.append(
            [
                "gh",
                "pr",
                "create",
                "--title",
                title,
                "--base",
                "develop",
                "--head",
                branch,
                "--body",
                "Update metadata and picture from Metadata Qt app",
            ]
        )
    return cmds


def _repo_root(start: Optional[str] = None) -> Optional[str]:
    base = start or os.getcwd()
    try:
        cp = _run(["git", "rev-parse", "--show-toplevel"], cwd=base)
        if cp.returncode == 0:
            return cp.stdout.strip()
    except Exception:
        pass
    return None


def _current_branch(repo: str) -> str:
    cp = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    return cp.stdout.strip()


def _ensure_fetched(repo: str) -> None:
    _run(["git", "fetch", "origin"], cwd=repo)


def _is_up_to_date(repo: str, branch: str = "develop") -> bool:
    # After fetch, check if local branch is exactly in sync with origin/branch (no ahead, no behind)
    cp = _run(
        ["git", "rev-list", "--left-right", "--count", f"{branch}...origin/{branch}"], cwd=repo
    )
    if cp.returncode != 0:
        return False
    out = (cp.stdout or "").strip()
    try:
        ahead_str, behind_str = out.split()
        ahead, behind = int(ahead_str), int(behind_str)
        return ahead == 0 and behind == 0
    except Exception:
        return False


def create_metadata_pr(
    changed_paths: list[str], speaker_key: str, *, repo_root: Optional[str] = None
) -> Tuple[bool, str]:
    root = repo_root or _repo_root()
    if not root:
        return False, "Not a Git repository"

    # Normalize paths to be relative to repo root for nicer git add
    files: list[str] = []
    for p in changed_paths:
        try:
            rp = os.path.relpath(p, root)
        except Exception:
            rp = p
        files.append(rp)

    _ensure_fetched(root)
    branch = _current_branch(root)
    up_to_date = _is_up_to_date(root, "develop")
    gh_available = bool(shutil.which("gh"))

    try:
        cmds = plan_pr_actions(
            current_branch=branch,
            up_to_date=up_to_date,
            files=files,
            speaker_key=speaker_key,
            date_str=today_str(),
            gh_available=gh_available,
        )
    except Exception as e:
        return False, str(e)

    for cmd in cmds:
        cp = _run(cmd, cwd=root)
        if cp.returncode != 0:
            return False, f"Command failed: {' '.join(cmd)}\n{cp.stderr}"

    return (
        True,
        "Pull request created and pushed (or branch pushed; create PR manually if gh not available).",
    )


def preflight_repo(
    *, repo_root: Optional[str] = None, required_branch: str = "develop"
) -> Tuple[bool, str]:
    """Check the repository is on required_branch and fully up-to-date with origin.

    Returns (ok, message). When ok is False, message explains the reason.
    """
    root = repo_root or _repo_root()
    if not root:
        return False, "Not a Git repository"
    try:
        _ensure_fetched(root)
    except Exception:
        # Non-fatal; continue checks
        pass
    branch = _current_branch(root)
    if branch != required_branch:
        return False, f"Repository is on '{branch}', expected '{required_branch}'"
    if not _is_up_to_date(root, required_branch):
        return False, f"Local '{required_branch}' is not up-to-date with 'origin/{required_branch}'"
    return True, "OK"
