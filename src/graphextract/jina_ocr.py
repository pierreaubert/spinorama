# -*- coding: utf-8 -*-
"""Transcription-grade OCR via jinaai/jina-ocr-v1 (DeepSeek-OCR backbone).

This model emits Markdown text, not word boxes, so it cannot implement
``OCRProvider.read_words``. Use it as a fallback/reconciliation source:
tick-label tokens and legend strings recovered from the transcription,
explicitly flagged as having no geometry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

MODEL_ID = "jinaai/jina-ocr-v1"

# Graph-tuned prompt: the default document prompt drops figure content,
# which on Klippel-style graphs includes the axis tick labels.
GRAPH_PROMPT = (
    "Transcribe every visible text element in this measurement graph image, "
    "including axis tick labels, axis titles and units, legend entries and "
    "panel titles, preserving reading order. Output plain text lines only, "
    "no tables, no commentary."
)

# Canonical CEA2034 series names we try to recover from legend text.
KNOWN_SERIES = (
    "On Axis",
    "Listening Window",
    "Early Reflections",
    "Sound Power",
    "Estimated In-Room Response",
    "Directivity Index",
)


def pick_device(preferred: str | None = None) -> str:
    """Best torch device on this machine: cuda > mps > cpu. Honors override."""
    if preferred:
        return preferred
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def pick_dtype(device: str):
    """bf16 where generation is fast (cuda/mps), fp32 on cpu."""
    import torch

    if device.startswith("cuda") or device == "mps":
        return torch.bfloat16
    return torch.float32


@dataclass
class JinaOCRReader:
    """Lazy wrapper around a local jina-ocr-v1 checkout."""

    model_id: str = MODEL_ID
    model_dir: str | None = None
    device: str | None = None
    max_new_tokens: int = 1024
    _model: object = field(default=None, repr=False)
    _processor: object = field(default=None, repr=False)

    def ensure_loaded(self) -> str:
        if self._model is not None:
            return self.device or "?"
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoProcessor
        except ImportError as exc:
            raise RuntimeError(
                "jina-ocr-v1 needs torch + transformers in the project venv: "
                "run scripts/jina_ocr_run.py --install-deps"
            ) from exc
        device = pick_device(self.device)
        if device.startswith("cuda") and not torch.cuda.is_available():
            raise RuntimeError(f"Requested {device} but CUDA is unavailable")
        torch_device = torch.device(device)
        src = self.model_dir or self.model_id
        self._processor = AutoProcessor.from_pretrained(src, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            src,
            dtype=pick_dtype(device),
            trust_remote_code=True,
        ).to(torch_device)
        self.device = device
        return device

    def transcribe(self, image_path: str, prompt: str | None = None) -> str:
        """Transcribe one image file to text. Raises on failure, never guesses.

        ``prompt=None`` keeps the processor default (upstream example.py
        behavior); pass GRAPH_PROMPT for measurement graphs.
        """
        from PIL import Image

        image = Image.open(image_path).convert("RGB")
        return self.transcribe_image(image, prompt=prompt)

    def transcribe_array(self, array, prompt: str | None = None) -> str:
        """Transcribe a BGR/gray/RGB ndarray without touching the filesystem."""
        import numpy as np
        from PIL import Image

        arr = np.asarray(array)
        if arr.ndim == 2:
            image = Image.fromarray(arr).convert("RGB")
        elif arr.shape[2] == 3:
            # OpenCV ordering; the vision tower is channel-order tolerant
            # for text, but convert properly instead of assuming.
            image = Image.fromarray(arr[:, :, ::-1])
        else:
            raise ValueError(f"Unsupported array shape {arr.shape}")
        return self.transcribe_image(image, prompt=prompt)

    def transcribe_image(self, image, prompt: str | None = None) -> str:
        """Transcribe a PIL RGB image to text."""
        device = self.ensure_loaded()
        import torch

        assert self._processor is not None and self._model is not None
        kwargs = {} if prompt is None else {"prompt": prompt}
        inputs = self._processor.prepare_ocr_inputs(
            image, device=torch.device(device), **kwargs
        )
        output = self._model.generate(
            **inputs,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
        )
        return self._processor.decode_ocr(output, inputs["input_ids"])


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_number_tokens(text: str) -> list[float]:
    """All numeric tokens in a transcription, in order of appearance."""
    return [float(m) for m in _NUMBER_RE.findall(text)]


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def extract_legend_candidates(text: str) -> list[str]:
    """Known CEA2034 series names mentioned in the transcription, in order."""
    norm = _normalize(text)
    return [name for name in KNOWN_SERIES if _normalize(name) in norm]
