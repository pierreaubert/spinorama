"""Import contract for the Spinorama 2.0 package layout."""

import importlib
import importlib.util

import pytest
import spinorama

CANONICAL_MODULES = (
    "spinorama.compute.cea2034",
    "spinorama.compute.estimates",
    "spinorama.compute.misc",
    "spinorama.compute.scores",
    "spinorama.extract.axis_calibrate",
    "spinorama.extract.color_segment",
    "spinorama.extract.curve_trace",
    "spinorama.extract.distortion",
    "spinorama.extract.plot_detect",
    "spinorama.filters.iir",
    "spinorama.filters.peq",
    "spinorama.filters.scores",
    "spinorama.loaders.gll_hv_txt",
    "spinorama.loaders.klippel",
    "spinorama.loaders.princeton",
    "spinorama.loaders.rew_eq",
    "spinorama.loaders.rew_impulse",
    "spinorama.loaders.rew_text_dump",
    "spinorama.loaders.spl_hv_txt",
    "spinorama.loaders.webplotdigitizer",
)

LEGACY_MODULES = (
    "spinorama.compute_cea2034",
    "spinorama.compute_estimates",
    "spinorama.compute_misc",
    "spinorama.compute_scores",
    "spinorama.extract_axis_calibrate",
    "spinorama.extract_color_segment",
    "spinorama.extract_curve_trace",
    "spinorama.extract_distortion",
    "spinorama.extract_plot_detect",
    "spinorama.filter_iir",
    "spinorama.filter_peq",
    "spinorama.filter_scores",
    "spinorama.load_gll_hv_txt",
    "spinorama.load_klippel",
    "spinorama.load_princeton",
    "spinorama.load_rew_eq",
    "spinorama.load_rew_impulse",
    "spinorama.load_rew_text_dump",
    "spinorama.load_spl_hv_txt",
    "spinorama.load_webplotdigitizer",
)

REPRESENTATIVE_EXPORTS = (
    ("spinorama.compute.cea2034", "compute_cea2034"),
    ("spinorama.extract.distortion", "extract_curves"),
    ("spinorama.filters.iir", "Biquad"),
    ("spinorama.loaders.klippel", "parse_graphs_speaker_klippel"),
)


def test_package_imports() -> None:
    assert spinorama.__name__ == "spinorama"


@pytest.mark.parametrize("module_name", CANONICAL_MODULES)
def test_canonical_module_imports(module_name: str) -> None:
    assert importlib.import_module(module_name).__name__ == module_name


@pytest.mark.parametrize(("module_name", "export_name"), REPRESENTATIVE_EXPORTS)
def test_canonical_module_exports(module_name: str, export_name: str) -> None:
    assert hasattr(importlib.import_module(module_name), export_name)


@pytest.mark.parametrize("module_name", LEGACY_MODULES)
def test_legacy_module_is_removed(module_name: str) -> None:
    assert importlib.util.find_spec(module_name) is None
