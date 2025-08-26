# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from typing import Any, Dict, Tuple

import typer
from typer.testing import CliRunner

import metahint.cli as cli


runner = CliRunner()


def test_scrape_cli_aggregates_and_calls_llm(monkeypatch):
    # Mock discovery to return two URLs
    def fake_discover(brand: str, model: str):
        return [
            "https://example.com/product",
            "https://example.com/manual",
        ]

    monkeypatch.setattr(cli, "discover_urls", fake_discover)

    # Mock fetch_url to return two simple HTML pages
    pages = {
        "https://example.com/product": (
            """
            <html><body>
            <table>
              <tr><th>Sensitivity</th><td>87 dB</td></tr>
              <tr><th>Frequency Response</th><td>45Hz - 20kHz</td></tr>
            </table>
            </body></html>
        """,
            "text/html",
        ),
        "https://example.com/manual": (
            """
            <html><body>
            <table>
              <tr><th>Minimum Impedance</th><td>4 Ohms</td></tr>
              <tr><th>Weight</th><td>30 lbs / 13.6 kg</td></tr>
            </table>
            </body></html>
        """,
            "text/html",
        ),
    }

    def fake_fetch(url: str, engine: str = "auto") -> Tuple[str, str]:  # noqa: ARG001
        return pages[url]

    monkeypatch.setattr(cli, "fetch_url", fake_fetch)

    # Mock LLM to contribute one more field
    def fake_llm(prompt: str, port: int):  # noqa: ARG001
        # Return a JSON-like mapping the normalizer can understand
        return {
            "overall frequency response": "40Hz - 20kHz",
            "sensitivity": "87 dB",
        }

    monkeypatch.setattr(cli, "_infer_with_llm", fake_llm)

    result = runner.invoke(
        cli.app, ["scrape", "Acme", "Model X", "--engine", "requests", "--port", "5555"]
    )
    assert result.exit_code == 0, result.output

    data = json.loads(result.stdout)
    # Ensure expected structure and fields exist
    assert "frequency_response_hz" in data
    overall = data["frequency_response_hz"]["overall"]
    # overall is ConfidenceValue -> dict with 'value' Range
    assert overall["value"]["min"] in (40.0, 45.0)
    assert overall["value"]["max"] == 20000.0

    sens = data["sensitivity_db_2p83v_1m"]
    assert sens["value"] == 87.0

    # Impedance and weight came from manual page
    assert data["impedance"]["min_ohms"]["value"] == 4.0
    assert "weight" in data


def test_fetcher_requests_engine(monkeypatch):
    # Test that fetch_url with requests engine uses requests.get
    import metahint.fetcher as fetcher

    class DummyResp:
        def __init__(self):
            self.status_code = 200
            self.text = "<html><title>ok</title></html>"
            self.headers = {"content-type": "text/html; charset=utf-8"}

        def raise_for_status(self):
            return None

    def fake_get(url: str, timeout: int = 20):  # noqa: ARG001
        return DummyResp()

    monkeypatch.setattr(fetcher, "requests", type("R", (), {"get": staticmethod(fake_get)}))

    content, mime = fetcher.fetch_url("https://example.com", engine="requests")
    assert "ok" in content
    assert mime == "text/html"
