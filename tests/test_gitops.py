from __future__ import annotations

import pytest

from metaedit.gitops import plan_pr_actions, sanitize_ref


def test_plan_pr_requires_develop_and_uptodate() -> None:
    files = ["datas/metadata_a.py", "datas/pictures/Genelec 8341A.png"]
    # Not on develop
    with pytest.raises(ValueError):
        plan_pr_actions(
            current_branch="main",
            up_to_date=True,
            files=files,
            speaker_key="Genelec 8341A",
            date_str="2025-08-26",
            gh_available=True,
        )
    # Not up-to-date
    with pytest.raises(ValueError):
        plan_pr_actions(
            current_branch="develop",
            up_to_date=False,
            files=files,
            speaker_key="Genelec 8341A",
            date_str="2025-08-26",
            gh_available=True,
        )


def test_plan_pr_commands_with_and_without_gh() -> None:
    files = ["datas/metadata_g.py", "datas/pictures/Genelec 8341A.png"]
    cmds = plan_pr_actions(
        current_branch="develop",
        up_to_date=True,
        files=files,
        speaker_key="Genelec 8341A",
        date_str="2025-08-26",
        gh_available=True,
    )
    # Switch branch command
    assert cmds[0][:3] == ["git", "switch", "-c"]
    # Add includes both files
    assert ["git", "add", *files] in cmds
    # Commit present
    assert any(c[:2] == ["git", "commit"] for c in cmds)
    # Push present
    assert ["git", "push", "-u", "origin", cmds[0][3]] in cmds
    # gh pr create present
    assert any(c[:3] == ["gh", "pr", "create"] for c in cmds)

    # Without gh, gh command omitted
    cmds2 = plan_pr_actions(
        current_branch="develop",
        up_to_date=True,
        files=files,
        speaker_key="Genelec 8341A",
        date_str="2025-08-26",
        gh_available=False,
    )
    assert not any(c and c[0] == "gh" for c in cmds2)


def test_sanitize_ref() -> None:
    assert sanitize_ref("Genelec 8341A") == "genelec-8341a"
    assert sanitize_ref("B&W 800 D3") == "b-w-800-d3"
    assert sanitize_ref("  ") == "meta"
