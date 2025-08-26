#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

import typer
from typer.testing import CliRunner

from metahint.cli import app as scrape_app

# Ground truth database
from datas.metadata import speakers_info  # type: ignore


@dataclass
class FieldResult:
    total: int = 0
    correct: int = 0

    def acc(self) -> float:
        return 0.0 if self.total == 0 else self.correct / self.total


def _get_default_specs(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    meas_key = entry.get("default_measurement")
    measurements = entry.get("measurements", {})
    block = measurements.get(meas_key) if isinstance(measurements, dict) else None
    if not block or not isinstance(block, dict):
        return None
    return block.get("specifications")


def _norm_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            return float(v.strip())
    except Exception:
        return None
    return None


def _close(a: Optional[float], b: Optional[float], tol_abs: float, tol_rel: float) -> bool:
    if a is None or b is None:
        return False
    if math.isclose(a, b, rel_tol=tol_rel, abs_tol=tol_abs):
        return True
    return False


def _extract_predicted_number(d: Dict[str, Any], path: List[str]) -> Optional[float]:
    # Walk down dict, last might be ConfidenceValue-like {value, confidence}
    cur: Any = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    if isinstance(cur, dict) and "value" in cur:
        v = cur["value"]
        if isinstance(v, dict) and "min" in v and "max" in v:
            # Range - choose nominal as max (Hz) or mean
            try:
                return float(v.get("min"))
            except Exception:
                return None
        return _norm_float(v)
    return _norm_float(cur)


def _compare_one(
    pred: Dict[str, Any], truth_specs: Dict[str, Any], results: Dict[str, FieldResult]
) -> None:
    # sensitivity (dB)
    if "sensitivity" in truth_specs:
        results.setdefault("sensitivity", FieldResult()).total += 1
        t = _norm_float(truth_specs.get("sensitivity"))
        p = _extract_predicted_number(pred, ["sensitivity_db_2p83v_1m"])
        if _close(p, t, tol_abs=1.5, tol_rel=0.05):
            results["sensitivity"].correct += 1

    # impedance nominal (ohms)
    if "impedance" in truth_specs:
        results.setdefault("impedance", FieldResult()).total += 1
        t = _norm_float(truth_specs.get("impedance"))
        p = _extract_predicted_number(pred, ["impedance", "nominal_ohms"])
        if p is None:  # fallback to min_ohms
            p = _extract_predicted_number(pred, ["impedance", "min_ohms"])
        if _close(p, t, tol_abs=1.0, tol_rel=0.2):
            results["impedance"].correct += 1

    # dimensions (mm)
    dim_truth = truth_specs.get("size")
    if isinstance(dim_truth, dict):
        for comp in ("height", "width", "depth"):
            if comp in dim_truth:
                key = f"dim_{comp}"
                results.setdefault(key, FieldResult()).total += 1
                t = _norm_float(dim_truth.get(comp))
                p = _extract_predicted_number(pred, ["dimensions", comp, "mm"])
                # allow 5% or 5mm
                if _close(p, t, tol_abs=5.0, tol_rel=0.05):
                    results[key].correct += 1

    # weight (kg)
    if "weight" in truth_specs:
        results.setdefault("weight", FieldResult()).total += 1
        t = _norm_float(truth_specs.get("weight"))
        p = _extract_predicted_number(pred, ["weight", "kg"])
        if _close(p, t, tol_abs=0.5, tol_rel=0.1):
            results["weight"].correct += 1


def _run_scrape(brand: str, model: str, engine: str, port: int) -> Optional[Dict[str, Any]]:
    runner = CliRunner()
    args = ["scrape", brand, model, "--engine", engine, "--port", str(port)]
    res = runner.invoke(scrape_app, args)
    if res.exit_code != 0:
        return None
    try:
        return json.loads(res.stdout)
    except Exception:
        return None


app = typer.Typer(help="Benchmark metahint accuracy against vetted metadata")


@app.command()
def main(
    n: int = typer.Option(10, "--n", help="Number of random speakers to evaluate"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for reproducibility"),
    engine: str = typer.Option("auto", "--engine", help="Fetcher engine: auto|requests|playwright"),
    port: int = typer.Option(1234, "--port", help="Local LLM port for supplementation"),
) -> None:
    if seed is not None:
        random.seed(seed)

    # Build population of candidates with identifiable brand/model
    population: List[Tuple[str, Dict[str, Any]]] = []
    for _, entry in speakers_info.items():
        if not isinstance(entry, dict):
            continue
        brand = entry.get("brand")
        model = entry.get("model")
        if not brand or not model:
            continue
        specs = _get_default_specs(entry)
        # keep only if we have some truth to compare
        if (
            specs
            and isinstance(specs, dict)
            and (
                "sensitivity" in specs
                or "impedance" in specs
                or "size" in specs
                or "weight" in specs
            )
        ):
            population.append((f"{brand} {model}", entry))

    if not population:
        typer.echo("No suitable entries with specifications found.")
        raise typer.Exit(code=1)

    sample = random.sample(population, k=min(n, len(population)))

    results: Dict[str, FieldResult] = {}
    evaluated = 0

    for label, entry in sample:
        brand = entry["brand"]
        model = entry["model"]
        truth_specs = _get_default_specs(entry)
        if not truth_specs:
            continue

        pred = _run_scrape(str(brand), str(model), engine=engine, port=port)
        if not pred:
            continue

        _compare_one(pred, truth_specs, results)
        evaluated += 1
        typer.echo(f"Evaluated: {label}")

    if evaluated == 0:
        typer.echo("No items successfully evaluated.")
        raise typer.Exit(code=1)

    # Report
    typer.echo("\nField accuracies:")
    overall_correct = 0
    overall_total = 0
    for k in sorted(results.keys()):
        r = results[k]
        overall_correct += r.correct
        overall_total += r.total
        typer.echo(f"- {k}: {r.correct}/{r.total} = {r.acc():.2%}")

    typer.echo("\nOverall accuracy:")
    if overall_total == 0:
        typer.echo("- n/a")
    else:
        typer.echo(f"- {overall_correct}/{overall_total} = {overall_correct / overall_total:.2%}")


if __name__ == "__main__":
    app()
