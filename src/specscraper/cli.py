# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import typer

from specscraper.discovery import discover_urls
from specscraper.fetcher import fetch_url
from specscraper.parsers.html_parser import parse_spec_key_values
from specscraper.parsers.normalizer import assemble_specs, normalize_raw_map
from specscraper.schema import ConfidenceValue
import time
import contextlib
import requests

app = typer.Typer(help="Discover and extract loudspeaker specifications")


@app.command()
def parse_local_html(
    html_path: Path = typer.Argument(
        ..., exists=True, readable=True, help="Path to a local HTML file"
    ),
    source_url: Optional[str] = typer.Option(None, help="Optional source URL to embed in output"),
    out: Optional[Path] = typer.Option(None, help="Write JSON to this path instead of stdout"),
) -> None:
    """Parse a local HTML file for specifications and emit normalized JSON."""
    text = html_path.read_text(encoding="utf-8")
    raw, _notes = parse_spec_key_values(text)
    norm = normalize_raw_map(raw)
    specs = assemble_specs(norm, source_url=source_url)

    data = json.loads(specs.model_dump_json())
    if out:
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        typer.echo(json.dumps(data, indent=2))


def _combine_conf(a: ConfidenceValue, b: ConfidenceValue) -> ConfidenceValue:
    """Combine two ConfidenceValue instances preferring higher confidence.

    If values differ at same confidence level, keep `a` but downgrade to medium.
    """
    order = {"low": 0, "medium": 1, "high": 2}
    if order.get(b.confidence, 0) > order.get(a.confidence, 0):
        return b
    if order.get(b.confidence, 0) == order.get(a.confidence, 0) and a.value != b.value:
        # disagree at same level -> downgrade
        return ConfidenceValue(value=a.value, confidence="medium", source_hint=a.source_hint)
    return a


def _aggregate_norms(norms: List[Dict]) -> Dict:
    """Merge multiple normalized maps by combining ConfidenceValue fields.

    Assumes each value is either ConfidenceValue, dict of ConfidenceValue, or plain.
    """
    out: Dict = {}
    for n in norms:
        for k, v in n.items():
            if k not in out:
                out[k] = v
            else:
                if isinstance(v, ConfidenceValue) and isinstance(out[k], ConfidenceValue):
                    out[k] = _combine_conf(out[k], v)  # type: ignore[arg-type]
                elif isinstance(v, dict) and isinstance(out[k], dict):
                    # merge nested dicts shallowly
                    merged = dict(out[k])
                    for sk, sv in v.items():
                        if sk not in merged:
                            merged[sk] = sv
                        else:
                            if isinstance(sv, ConfidenceValue) and isinstance(
                                merged[sk], ConfidenceValue
                            ):
                                merged[sk] = _combine_conf(merged[sk], sv)  # type: ignore[arg-type]
                            else:
                                merged[sk] = sv
                    out[k] = merged
                else:
                    out[k] = v
    return out


def _infer_with_llm(prompt: str, port: int) -> Optional[Dict[str, str]]:
    """Call a local LLM server to extract key-value specs from text.

    Tries an OpenAI-compatible endpoint on /v1/chat/completions; falls back to /extract.
    Expects a JSON object of key->value strings in the response.
    """
    base = f"http://127.0.0.1:{port}"
    headers = {"Content-Type": "application/json"}
    # Try OpenAI-compatible
    payload = {
        "model": "local",
        "messages": [
            {
                "role": "system",
                "content": "Extract loudspeaker spec key/value pairs as a flat JSON object.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
    }
    with contextlib.suppress(Exception):
        r = requests.post(
            f"{base}/v1/chat/completions", headers=headers, data=json.dumps(payload), timeout=30
        )
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        # Try to parse JSON from content
        with contextlib.suppress(Exception):
            return json.loads(content)
    # Fallback simple endpoint
    with contextlib.suppress(Exception):
        r = requests.post(
            f"{base}/extract", headers=headers, data=json.dumps({"text": prompt}), timeout=30
        )
        r.raise_for_status()
        return r.json()
    return None


@app.command()
def scrape(
    brand: str = typer.Argument(..., help="Brand name"),
    model: str = typer.Argument(..., help="Model name"),
    out: Optional[Path] = typer.Option(None, help="Write JSON to this path instead of stdout"),
    engine: str = typer.Option("auto", help="Fetch engine: auto|requests|playwright"),
    port: int = typer.Option(1234, "--port", help="Local LLM port for assisted extraction"),
) -> None:
    """Discover product pages and manuals, extract specs, and aggregate with confidence.

    Strategy:
    - Discover candidate URLs for brand/model
    - Fetch content from each URL (HTML)
    - Extract raw key/values (regex/HTML parser)
    - Normalize and aggregate candidate fields across sources
    - Supplement with local LLM extraction to improve coverage
    """
    candidates: List[Tuple[str, str]] = []  # (url, mime)

    # 1) Discover URLs
    urls = discover_urls(brand, model)
    # Always include a naive guess: brand site search page (best-effort, non-fatal)
    with contextlib.suppress(Exception):
        urls.extend(
            list(
                {
                    f"https://www.google.com/search?q={brand}+{model}+site:{brand.lower()}.com",
                    f"https://duckduckgo.com/?q={brand}+{model}+manual",
                }
            )
        )

    # 2) Fetch
    raw_pages: List[Tuple[str, str]] = []  # (source_url, html)
    for u in urls[:5]:  # limit for safety
        with contextlib.suppress(Exception):
            html, mime = fetch_url(u, engine=engine)  # type: ignore[arg-type]
            if mime.startswith("text/html"):
                raw_pages.append((u, html))
                # be gentle if dynamic fetching
                time.sleep(0.2)

    # 3) Parse and normalize
    norm_list: List[Dict] = []
    for source_url, html in raw_pages:
        raw_map, _notes = parse_spec_key_values(html)
        norm = normalize_raw_map(raw_map)
        # attach source hints where missing
        for k, v in list(norm.items()):
            if isinstance(v, ConfidenceValue) and v.source_hint is None:
                norm[k] = ConfidenceValue(
                    value=v.value, confidence=v.confidence, source_hint="specs_html"
                )
        norm_list.append(norm)

    # 4) LLM supplementation
    combined_text = "\n\n".join([h for _, h in raw_pages][:2])  # short prompt
    if combined_text:
        llm_map = _infer_with_llm(f"Brand: {brand}\nModel: {model}\n\nText:\n{combined_text}", port)
        if llm_map:
            llm_norm = normalize_raw_map(llm_map)
            norm_list.append(llm_norm)

    # 5) Aggregate
    aggregated = _aggregate_norms(norm_list)
    specs = assemble_specs(aggregated, source_url=urls[0] if urls else None)

    data = json.loads(specs.model_dump_json())
    if out:
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        typer.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    app()
