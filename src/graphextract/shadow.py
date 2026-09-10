# -*- coding: utf-8 -*-
"""Shadow deployment + qualification (plan-20260810, sections 8-10).

A candidate runs beside the incumbent over the corpus; promotion requires the
locked-set gates below. Pointers live in ``pointers/``: ``promoted.json`` names
the serving candidate, ``history.jsonl`` records every decision. Rollback
restores the previous pointer. Nothing here retrains; training candidates
arrive via training.RunManifest artefacts.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from graphextract.pipeline import AxisAnchors, run_panel
from graphextract.schema import PanelOutcome
from graphextract.tracking import TrackConfig

POINTERS_DIR = Path("pointers")


@dataclass
class Candidate:
    name: str
    track: dict = field(default_factory=dict)  # TrackConfig kwargs
    evidence_cleanup: bool = False  # preview-only morphology; expected to hurt
    notes: str = ""

    def track_config(self) -> TrackConfig:
        return TrackConfig(**self.track)


def run_candidate(img, panel_id: str, interior, offset, anchors: AxisAnchors,
                  styles, cand: Candidate):
    """Execute one panel under a candidate config (evidence flag via segment hook)."""
    if not cand.evidence_cleanup:
        return run_panel(img, panel_id, interior, offset, anchors, styles,
                         cand.track_config() if cand.track else None)
    # Destructive variant for gate validation: route through cleaned evidence.
    import cv2
    from graphextract.evidence import segment_evidence
    from graphextract.pipeline import PIPELINE_VERSION
    from graphextract.tracking import track_panel as _track

    res = run_panel(img, panel_id, interior, offset, anchors, styles,
                    cand.track_config() if cand.track else None)
    gray = cv2.cvtColor(interior, cv2.COLOR_BGR2GRAY) if interior.ndim == 3 else interior
    layers = segment_evidence(interior, styles, cleanup=True)
    tracks = _track(gray, layers, [s.series_id for s in styles], float(np.median(gray)),
                    cand.track_config() if cand.track else None)
    ox, oy = offset
    for tr in res.series:
        sm = tracks.get(tr.series_id)
        if sm is None:
            continue
        for s, q in zip(tr.samples, sm.samples):
            s.status = q.status
            if s.status.value == "observed":
                s.u, s.v = q.u + ox, q.v + oy
    res.provenance["candidate"] = cand.name
    res.provenance["pipeline"] = PIPELINE_VERSION
    return res


@dataclass
class GateResult:
    passed: bool
    details: dict


def check_gates(incumbent: dict, candidate: dict) -> GateResult:
    """Promote only on: no new FAILED panels, acceptance not worse, strict not worse."""
    details = {
        "failed_delta": candidate["n_failed"] - incumbent["n_failed"],
        "accept_delta": candidate["accept_rate"] - incumbent["accept_rate"],
        "strict_delta": candidate["strict_rate"] - incumbent["strict_rate"],
    }
    passed = (details["failed_delta"] <= 0 and details["accept_delta"] >= 0
              and details["strict_delta"] >= 0)
    return GateResult(passed, details)


def summarize_results(results: list[dict]) -> dict:
    n = len(results)
    failed = sum(1 for r in results if r["outcome"] == PanelOutcome.FAILED.value)
    accept = sum(1 for r in results if r["outcome"] == PanelOutcome.COMPLETE.value)
    strict = sum(1 for r in results if r.get("strict_all"))
    return {"n": n, "n_failed": failed,
            "accept_rate": accept / n if n else 0.0,
            "strict_rate": strict / n if n else 0.0}


def shadow_compare(items: list[dict], incumbent: Candidate,
                   candidates: list[Candidate]) -> dict:
    """Run incumbent + candidates over items; items hold img/interior/anchors/styles.

    Each item may carry ``strict_checker``: a zero-arg callable returning True
    when every series of a PanelResult passes the strict test (used on gold).
    """
    report: dict = {"incumbent": incumbent.name, "candidates": {}}
    for cand in [incumbent, *candidates]:
        rows = []
        for it in items:
            res = run_candidate(it["img"], it["panel_id"], it["interior"], it["offset"],
                                it["anchors"], it["styles"], cand)
            row = {"panel_id": it["panel_id"], "outcome": res.outcome.value}
            checker = it.get("strict_checker")
            if checker is not None:
                try:
                    row["strict_all"] = bool(checker(res))
                except Exception:
                    row["strict_all"] = False
            rows.append(row)
        report["candidates"][cand.name] = {"summary": summarize_results(rows), "rows": rows}
    base = report["candidates"][incumbent.name]["summary"]
    for cand in candidates:
        summ = report["candidates"][cand.name]["summary"]
        gate = check_gates(base, summ)
        report["candidates"][cand.name]["gate"] = {"passed": gate.passed,
                                                   "details": gate.details}
    return report


def promote(candidate_name: str, report: dict,
            pointers_dir: str | Path = POINTERS_DIR) -> Path:
    """Record promotion; the previous pointer is kept in history for rollback."""
    d = Path(pointers_dir)
    d.mkdir(parents=True, exist_ok=True)
    prev = None
    p = d / "promoted.json"
    if p.exists():
        prev = json.loads(p.read_text(encoding="utf-8"))
    entry = {"name": candidate_name, "timestamp": time.time(),
             "gate": report["candidates"][candidate_name].get("gate")}
    if entry["gate"] is not None and not entry["gate"]["passed"]:
        raise ValueError(f"refusing to promote {candidate_name}: gates did not pass")
    p.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    with open(d / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"action": "promote", "entry": entry, "previous": prev}) + "\n")
    return p


def rollback(pointers_dir: str | Path = POINTERS_DIR) -> dict:
    """Restore the previous pointer; raises when there is nothing to roll back to."""
    d = Path(pointers_dir)
    hist = d / "history.jsonl"
    if not hist.exists():
        raise ValueError("no promotion history; nothing to roll back")
    lines = hist.read_text(encoding="utf-8").strip().split("\n")
    last = json.loads(lines[-1])
    prev = last.get("previous")
    if not prev:
        raise ValueError("no previous pointer recorded; nothing to roll back")
    (d / "promoted.json").write_text(json.dumps(prev, indent=2) + "\n", encoding="utf-8")
    with open(hist, "a", encoding="utf-8") as f:
        f.write(json.dumps({"action": "rollback", "restored": prev}) + "\n")
    return prev


def current(pointers_dir: str | Path = POINTERS_DIR) -> dict | None:
    p = Path(pointers_dir) / "promoted.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
