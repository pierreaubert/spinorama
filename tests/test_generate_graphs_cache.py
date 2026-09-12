"""Regression tests for incremental speaker-graph fingerprints."""

import hashlib
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# Importing generate_common first: it restores the np.unicode_/np.string_
# aliases flammkuchen 1.0.3 needs under NumPy 2.x (see generate_common.py).
import generate_common
import generate_graphs


class TestGraphFingerprint(unittest.TestCase):
    def test_isolated_from_unrelated_metadata_but_tracks_its_own_inputs(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            data_root = Path(temporary_dir)
            measurement = data_root / "datas" / "measurements" / "Test Speaker" / "spin.txt"
            measurement.parent.mkdir(parents=True)
            measurement.write_text("first\n", encoding="utf-8")

            speakers = {
                "Test Speaker": {"model": "Test Speaker", "value": 1},
                "Other Speaker": {"model": "Other Speaker", "value": 1},
            }
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                shared = generate_graphs.graph_generator_fingerprint(str(data_root), 600, 400)
                first = generate_graphs.speaker_graph_fingerprint(
                    str(data_root), "Test Speaker", 600, 400, shared
                )

                speakers["Other Speaker"]["value"] = 2
                self.assertEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )

                speakers["Test Speaker"]["value"] = 2
                self.assertNotEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )

                speakers["Test Speaker"]["value"] = 1
                measurement.write_text("second\n", encoding="utf-8")
                stats = measurement.stat()
                os.utime(measurement, ns=(stats.st_atime_ns, stats.st_mtime_ns + 1_000_000))
                self.assertNotEqual(
                    first,
                    generate_graphs.speaker_graph_fingerprint(
                        str(data_root), "Test Speaker", 600, 400, shared
                    ),
                )


class TestVersionFingerprint(unittest.TestCase):
    def _make_tree(self, root: Path) -> dict:
        (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
        (root / "datas" / "measurements" / "Speaker X" / "v2").mkdir(parents=True)
        (root / "datas" / "eq" / "Speaker X").mkdir(parents=True)
        (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
            "v1\n", encoding="utf-8"
        )
        (root / "datas" / "measurements" / "Speaker X" / "v2" / "data.txt").write_text(
            "v2\n", encoding="utf-8"
        )
        (root / "datas" / "eq" / "Speaker X" / "iir.txt").write_text("eq\n", encoding="utf-8")
        return {
            "format": "klippel",
            "origin": "ASR",
            "review": "https://example.com/review",
            "review_published": "20200101",
        }

    def _fingerprint(self, root: Path, measurement: dict, version: str = "v1") -> str:
        generator = generate_graphs.graph_generator_fingerprint(str(root), 600, 400)
        return generate_graphs.version_graph_fingerprint(
            str(root), "Speaker X", version, measurement, "Brand", "bookshelves", generator
        )

    def test_isolated_from_other_versions_and_display_metadata(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            measurement = self._make_tree(root)
            first = self._fingerprint(root, measurement)
            self.assertEqual(first, self._fingerprint(root, dict(measurement)))

            # Another version's files do not affect this version.
            (root / "datas" / "measurements" / "Speaker X" / "v2" / "data.txt").write_text(
                "v2 changed\n", encoding="utf-8"
            )
            self.assertEqual(first, self._fingerprint(root, measurement))

            # Display-only metadata does not invalidate graph output.
            measurement["review_published"] = "20210101"
            self.assertEqual(first, self._fingerprint(root, dict(measurement)))

            # Graph inputs do invalidate it.
            measurement["format"] = "princeton"
            self.assertNotEqual(first, self._fingerprint(root, dict(measurement)))

    def test_ignores_mtime_only_touches_and_absolute_prefix(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            measurement = self._make_tree(root)
            first = self._fingerprint(root, measurement)

            # Same bytes with a bumped mtime must not invalidate the entry.
            data_file = root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt"
            stats = data_file.stat()
            os.utime(data_file, ns=(stats.st_atime_ns, stats.st_mtime_ns + 5_000_000_000))
            self.assertEqual(first, self._fingerprint(root, measurement))

            # The same tree under another absolute prefix fingerprints identically.
            with tempfile.TemporaryDirectory() as other_dir:
                other_root = Path(other_dir) / "nested" / "data"
                shutil.copytree(root, other_root)
                self.assertEqual(first, self._fingerprint(other_root, measurement))

            # Different bytes do invalidate it.
            data_file.write_text("v1 changed\n", encoding="utf-8")
            self.assertNotEqual(first, self._fingerprint(root, measurement))


class TestVersionOutputFresh(unittest.TestCase):
    def test_requires_base_and_eq_json(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            dist = os.path.join(temporary_dir, "dist", "speakers")
            base = os.path.join(dist, "Speaker X", "ASR", "v1")
            os.makedirs(base)
            Path(os.path.join(base, "CEA2034.json")).write_text("{}", encoding="utf-8")

            fresh = generate_graphs.version_output_fresh
            self.assertTrue(fresh(dist, "Speaker X", "ASR", "v1", needs_eq=False))
            self.assertFalse(fresh(dist, "Speaker X", "ASR", "v1", needs_eq=True))

            os.makedirs(f"{base}_eq")
            Path(os.path.join(f"{base}_eq", "CEA2034.json")).write_text("{}", encoding="utf-8")
            self.assertTrue(fresh(dist, "Speaker X", "ASR", "v1", needs_eq=True))

            # Empty JSON files do not count as output.
            Path(os.path.join(base, "CEA2034.json")).write_text("", encoding="utf-8")
            self.assertFalse(fresh(dist, "Speaker X", "ASR", "v1", needs_eq=False))

    def test_strips_vendors_prefix_like_build_filename(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            dist = os.path.join(temporary_dir, "dist", "speakers")
            base = os.path.join(dist, "Speaker X", "ABC", "v1")
            os.makedirs(base)
            Path(os.path.join(base, "CEA2034.json")).write_text("{}", encoding="utf-8")
            self.assertTrue(
                generate_graphs.version_output_fresh(
                    dist, "Speaker X", "Vendors-ABC", "v1", needs_eq=False
                )
            )


class TestStaleDecisions(unittest.TestCase):
    def _setup(self, root: Path):
        data_root = str(root)
        (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
        (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
            "v1\n", encoding="utf-8"
        )
        speakers = {
            "Speaker X": {
                "brand": "Brand",
                "shape": "bookshelves",
                "measurements": {"v1": {"format": "klippel", "origin": "ASR"}},
            }
        }
        cache_dir = os.path.join(data_root, ".cache")
        dist_root = os.path.join(data_root, "dist", "speakers")
        return data_root, cache_dir, dist_root, speakers

    def _decide(self, data_root, cache_dir, dist_root, manifest_speakers):
        generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
        return generate_graphs._decide_stale_versions(
            {"Speaker X": "Speaker X"},
            manifest_speakers,
            generator,
            False,
            data_root,
            dist_root,
            cache_dir,
            False,
            False,
            None,
        )

    def _write_outputs_and_shard(self, dist_root, cache_dir):
        out_dir = os.path.join(dist_root, "Speaker X", "ASR", "v1")
        os.makedirs(out_dir)
        Path(os.path.join(out_dir, "CEA2034.json")).write_text("{}", encoding="utf-8")
        os.makedirs(cache_dir, exist_ok=True)
        Path(os.path.join(cache_dir, f"{generate_common.cache_key('Speaker X')}.h5")).write_bytes(
            b""
        )

    def test_cold_then_warm_then_each_invalidation(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            data_root, cache_dir, dist_root, speakers = self._setup(root)
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                fingerprints, stale, _old, invalid, _ex = self._decide(
                    data_root, cache_dir, dist_root, {}
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["missing_manifest"], 1)

                manifest = {
                    "Speaker X": {
                        "versions": {
                            "v1": {"fingerprint": fingerprints[("Speaker X", "v1")], "complete": True}
                        }
                    }
                }
                # Outputs and shard missing: still stale.
                _fp, stale, _o, invalid, _e = self._decide(
                    data_root, cache_dir, dist_root, manifest
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["output"], 1)

                self._write_outputs_and_shard(dist_root, cache_dir)
                _fp, stale, old_complete, _i, _e = self._decide(
                    data_root, cache_dir, dist_root, manifest
                )
                self.assertEqual(stale, set())
                self.assertTrue(old_complete[("Speaker X", "v1")])

                # Changed input bytes invalidate the warm entry.
                (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
                    "v1 changed\n", encoding="utf-8"
                )
                _fp, stale, _o, invalid, _e = self._decide(
                    data_root, cache_dir, dist_root, manifest
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["fingerprint"], 1)

    def test_incomplete_and_missing_shard_are_stale(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            data_root, cache_dir, dist_root, speakers = self._setup(root)
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
                info = speakers["Speaker X"]
                fingerprint, _ = generate_graphs._version_cache_entry(
                    data_root, "Speaker X", "v1", info["measurements"]["v1"],
                    info["brand"], info["shape"], generator,
                )
                self._write_outputs_and_shard(dist_root, cache_dir)
                manifest = {
                    "Speaker X": {"versions": {"v1": {"fingerprint": fingerprint, "complete": False}}}
                }
                _fp, stale, _o, invalid, _e = generate_graphs._decide_stale_versions(
                    {"Speaker X": "Speaker X"}, manifest, generator, False,
                    data_root, dist_root, cache_dir, False, False, None,
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["incomplete"], 1)

                manifest["Speaker X"]["versions"]["v1"]["complete"] = True
                os.unlink(
                    os.path.join(
                        cache_dir,
                        f"{generate_common.cache_key('Speaker X')}.h5",
                    )
                )
                _fp, stale, _o, invalid, _e = generate_graphs._decide_stale_versions(
                    {"Speaker X": "Speaker X"}, manifest, generator, False,
                    data_root, dist_root, cache_dir, False, False, None,
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["shard"], 1)


class TestManifestRoundTrip(unittest.TestCase):
    def test_save_then_reuse_and_refresh(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
            (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
                "v1\n", encoding="utf-8"
            )
            speakers = {
                "Speaker X": {
                    "brand": "Brand",
                    "shape": "bookshelves",
                    "measurements": {"v1": {"format": "klippel", "origin": "ASR"}},
                }
            }
            data_root = str(root)
            cache_dir = os.path.join(data_root, ".cache")
            dist_root = os.path.join(data_root, "dist", "speakers")
            manifest_path = os.path.join(cache_dir, "manifest.json")
            current = {"Speaker X": "Speaker X"}
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
                decide = generate_graphs._decide_stale_versions
                fingerprints, stale, _o, _i, _e = decide(
                    current, {}, generator, True,
                    data_root, dist_root, cache_dir, False, False, None,
                )
                self.assertEqual(stale, {("Speaker X", "v1")})

                generate_graphs._save_full_manifest(
                    manifest_path, generator, current, fingerprints,
                    {("Speaker X", "v1"): True},
                )
                out_dir = os.path.join(dist_root, "Speaker X", "ASR", "v1")
                os.makedirs(out_dir)
                Path(os.path.join(out_dir, "CEA2034.json")).write_text("{}", encoding="utf-8")
                os.makedirs(cache_dir, exist_ok=True)
                Path(
                    os.path.join(cache_dir, f"{generate_common.cache_key('Speaker X')}.h5")
                ).write_bytes(b"")

                reloaded = generate_common.load_cache_manifest(manifest_path)
                self.assertTrue(reloaded["cache_verified"])
                _fp, stale, _o, _i, _e = decide(
                    current, reloaded["speakers"], generator, False,
                    data_root, dist_root, cache_dir, False, False, None,
                )
                self.assertEqual(stale, set())

                # The --update-cache refresh path records processed versions.
                reloaded["speakers"]["Speaker X"]["versions"] = {}
                generate_common.save_cache_manifest(reloaded, manifest_path)
                generate_graphs._refresh_manifest_entries(
                    manifest_path, data_root, current, 600, 400,
                    {"Speaker X": {"ASR": {"v1": object(), "v1_eq": object()}}},
                )
                refreshed = generate_common.load_cache_manifest(manifest_path)
                entry = refreshed["speakers"]["Speaker X"]["versions"]["v1"]
                self.assertTrue(entry["complete"])
                self.assertEqual(entry["fingerprint"], fingerprints[("Speaker X", "v1")])


class TestV3Migration(unittest.TestCase):
    def test_adopts_verified_v3_entries_when_inputs_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
            (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
                "v1\n", encoding="utf-8"
            )
            speakers = {
                "Speaker X": {
                    "brand": "Brand",
                    "shape": "bookshelves",
                    "measurements": {"v1": {"format": "klippel", "origin": "ASR"}},
                }
            }
            data_root = str(root)
            cache_dir = os.path.join(data_root, ".cache")
            dist_root = os.path.join(data_root, "dist", "speakers")
            out_dir = os.path.join(dist_root, "Speaker X", "ASR", "v1")
            os.makedirs(out_dir)
            Path(os.path.join(out_dir, "CEA2034.json")).write_text("{}", encoding="utf-8")
            os.makedirs(cache_dir, exist_ok=True)
            Path(
                os.path.join(cache_dir, f"{generate_common.cache_key('Speaker X')}.h5")
            ).write_bytes(b"")

            v3_manifest = {"Speaker X": {"fingerprint": "legacy-v3-value"}}
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
                decide = generate_graphs._decide_stale_versions
                # Manifest newer than every input: adopt without reprocessing.
                _fp, stale, old_complete, _i, _e = decide(
                    {"Speaker X": "Speaker X"}, v3_manifest, generator, True,
                    data_root, dist_root, cache_dir, False, True, time.time_ns() + 10**9,
                )
                self.assertEqual(stale, set())
                self.assertTrue(old_complete[("Speaker X", "v1")])

                # Manifest older than the inputs: revalidate instead.
                _fp, stale, _o, invalid, _e = decide(
                    {"Speaker X": "Speaker X"}, v3_manifest, generator, True,
                    data_root, dist_root, cache_dir, False, True, 1,
                )
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["fingerprint"], 1)

    def test_unverified_v3_adopts_only_verified_versions(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
            (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
                "v1\n", encoding="utf-8"
            )
            speakers = {
                "Speaker X": {
                    "brand": "Brand",
                    "shape": "bookshelves",
                    "measurements": {"v1": {"format": "klippel", "origin": "ASR"}},
                }
            }
            data_root = str(root)
            cache_dir = os.path.join(data_root, ".cache")
            dist_root = os.path.join(data_root, "dist", "speakers")
            out_dir = os.path.join(dist_root, "Speaker X", "ASR", "v1")
            os.makedirs(out_dir)
            Path(os.path.join(out_dir, "CEA2034.json")).write_text("{}", encoding="utf-8")
            os.makedirs(cache_dir, exist_ok=True)
            Path(
                os.path.join(cache_dir, f"{generate_common.cache_key('Speaker X')}.h5")
            ).write_bytes(b"")

            v3_manifest = {"Speaker X": {"fingerprint": "legacy-v3-value"}}
            decide = generate_graphs._decide_stale_versions
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
                kwargs = {
                    "current_speakers": {"Speaker X": "Speaker X"},
                    "manifest_speakers": v3_manifest,
                    "generator": generator,
                    "generator_changed": True,
                    "data_root": data_root,
                    "dist_speakers_root": dist_root,
                    "cache_dir": cache_dir,
                    "force": False,
                    "migrating_v3": False,
                    "manifest_mtime_ns": time.time_ns() + 10**9,
                }
                # Not in the verified set: stale.
                _fp, stale, _o, invalid, _e = decide(**kwargs)
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["fingerprint"], 1)

                # Verified present in cache: adopted.
                _fp, stale, old_complete, _i, _e = decide(
                    **{**kwargs, "verified_versions": {("Speaker X", "v1")}}
                )
                self.assertEqual(stale, set())
                self.assertTrue(old_complete[("Speaker X", "v1")])


class TestInterruptedAccumulation(unittest.TestCase):
    def _answer(self, speaker, mversion, *, ok=True):
        return (ok, speaker, "ASR", mversion, {"df": object(), "eq": object()}, None)

    def test_keeps_partial_results_on_keyboard_interrupt(self):
        answers = iter(
            [
                self._answer("Speaker A", "v1"),
                self._answer("Speaker B", "v1", ok=False),
            ]
        )

        def interrupting(results):
            yield from results
            raise KeyboardInterrupt

        data_frame, succeeded, errors, interrupted = generate_graphs._accumulate_pool_results(
            interrupting(answers), 3
        )
        self.assertTrue(interrupted)
        self.assertEqual(succeeded, 1)
        self.assertEqual(errors, 1)
        self.assertIn("Speaker A", data_frame)
        self.assertNotIn("Speaker B", data_frame)

    def test_clean_run_is_not_flagged_interrupted(self):
        answers = [self._answer("Speaker A", "v1")]
        data_frame, succeeded, errors, interrupted = generate_graphs._accumulate_pool_results(
            iter(answers), 1
        )
        self.assertFalse(interrupted)
        self.assertEqual((succeeded, errors), (1, 0))
        self.assertIn("Speaker A", data_frame)


class TestGeneratorMechanism(unittest.TestCase):
    def _code_fp(self, func):
        digest = hashlib.sha256()
        generate_graphs._feed_code(digest, func.__code__)
        return digest.hexdigest()

    def test_bytecode_ignores_comments_but_tracks_logic(self):
        first = compile("def f(x):\n    # comment A\n    return x + 1\n", "<a>", "exec")
        second = compile("def f(x):\n    # comment B\n    return x + 1\n", "<b>", "exec")
        third = compile("def f(x):\n    return x + 2\n", "<c>", "exec")
        namespaces = [{} for _ in range(3)]
        for tree, namespace in zip((first, second, third), namespaces, strict=True):
            exec(tree, namespace)  # noqa: S102 -- compiling test fixtures, not user input
        self.assertEqual(self._code_fp(namespaces[0]["f"]), self._code_fp(namespaces[1]["f"]))
        self.assertNotEqual(self._code_fp(namespaces[0]["f"]), self._code_fp(namespaces[2]["f"]))

    def test_controller_script_excluded_from_rendering_files(self):
        self.assertNotIn(
            os.path.abspath(generate_graphs.__file__), generate_graphs._rendering_code_files()
        )
        # The controller fingerprint is stable across calls (deterministic).
        self.assertEqual(
            generate_graphs._controller_code_fingerprint(),
            generate_graphs._controller_code_fingerprint(),
        )

    def test_legacy_bridge_adopts_proven_versions(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "datas" / "measurements" / "Speaker X" / "v1").mkdir(parents=True)
            (root / "datas" / "measurements" / "Speaker X" / "v1" / "data.txt").write_text(
                "v1\n", encoding="utf-8"
            )
            speakers = {
                "Speaker X": {
                    "brand": "Brand",
                    "shape": "bookshelves",
                    "measurements": {"v1": {"format": "klippel", "origin": "ASR"}},
                }
            }
            data_root = str(root)
            cache_dir = os.path.join(data_root, ".cache")
            dist_root = os.path.join(data_root, "dist", "speakers")
            out_dir = os.path.join(dist_root, "Speaker X", "ASR", "v1")
            os.makedirs(out_dir)
            Path(os.path.join(out_dir, "CEA2034.json")).write_text("{}", encoding="utf-8")
            os.makedirs(cache_dir, exist_ok=True)
            Path(
                os.path.join(cache_dir, f"{generate_common.cache_key('Speaker X')}.h5")
            ).write_bytes(b"")
            with patch.object(generate_graphs.metadata, "speakers_info", speakers):
                generator = generate_graphs.graph_generator_fingerprint(data_root, 600, 400)
                self.assertIn(generate_graphs.GENERATOR_MECHANISM, generator)
                info = speakers["Speaker X"]
                # The stored entry was proven under a previous generator
                # mechanism, so it cannot match the current fingerprint; the
                # bridge re-derives it with the stored generator as salt.
                legacy_generator = "previous-mechanism-digest"
                legacy_fp, _ = generate_graphs._version_cache_entry(
                    data_root, "Speaker X", "v1", info["measurements"]["v1"],
                    info["brand"], info["shape"], legacy_generator,
                )
                current_fp, _ = generate_graphs._version_cache_entry(
                    data_root, "Speaker X", "v1", info["measurements"]["v1"],
                    info["brand"], info["shape"], generator,
                )
                self.assertNotEqual(legacy_fp, current_fp)
                manifest = {
                    "Speaker X": {
                        "versions": {"v1": {"fingerprint": legacy_fp, "complete": True}}
                    }
                }
                decide = generate_graphs._decide_stale_versions
                base = {
                    "current_speakers": {"Speaker X": "Speaker X"},
                    "manifest_speakers": manifest,
                    "generator": generator,
                    "generator_changed": True,
                    "data_root": data_root,
                    "dist_speakers_root": dist_root,
                    "cache_dir": cache_dir,
                    "force": False,
                    "migrating_v3": False,
                    "manifest_mtime_ns": None,
                }
                _fp, stale, _o, invalid, _e = decide(**base)
                self.assertEqual(stale, {("Speaker X", "v1")})
                self.assertEqual(invalid["fingerprint"], 1)

                _fp, stale, old_complete, _i, _e = decide(
                    **{**base, "legacy_bridge": True, "legacy_generator": legacy_generator}
                )
                self.assertEqual(stale, set())
                self.assertTrue(old_complete[("Speaker X", "v1")])

                # A wrong salt does not adopt.
                _fp, stale, _o, _i, _e = decide(
                    **{**base, "legacy_bridge": True, "legacy_generator": "wrong-salt"}
                )
                self.assertEqual(stale, {("Speaker X", "v1")})


class TestWorkerErrorContract(unittest.TestCase):
    def test_failure_returns_error_instead_of_none(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            task = (
                "Missing Speaker",
                "Missing Speaker",
                "NoOrigin",
                "v1",
                "bogus-format",
                "Brand",
                "bookshelves",
                None,
                None,
                1.0,
                1200,
                800,
                logging.WARNING,
                temporary_dir,
                os.path.join(temporary_dir, "dist", "speakers"),
                False,
            )
            answer = generate_graphs.process_single_measurement(task)
            self.assertIsNotNone(answer)
            success, speaker, origin, mversion, _result, error = answer
            self.assertFalse(success)
            self.assertIsNotNone(error)
            self.assertIsInstance(error, Exception)
            self.assertEqual((speaker, origin, mversion), ("Missing Speaker", "NoOrigin", "v1"))


class TestIncrementalCacheSave(unittest.TestCase):
    def test_only_affected_shards_are_rewritten(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            cache_dir = os.path.join(temporary_dir, ".cache")
            speaker_a, speaker_b = "Speaker A", "Speaker B"
            shard_a = os.path.join(cache_dir, f"{generate_common.cache_key(speaker_a)}.h5")

            generate_common.cache_save_incremental(
                {speaker_a: {"O": {"v": np.array([1.0])}}},
                {speaker_a},
                set(),
                cache_dir=cache_dir,
                prune=True,
            )
            self.assertTrue(os.path.isfile(shard_a))
            mtime_before = os.stat(shard_a).st_mtime_ns

            generate_common.cache_save_incremental(
                {speaker_b: {"O": {"v": np.array([2.0])}}},
                {speaker_a, speaker_b},
                set(),
                cache_dir=cache_dir,
                prune=True,
            )
            # The untouched speaker's shard must not be rewritten.
            self.assertEqual(mtime_before, os.stat(shard_a).st_mtime_ns)

            loaded = generate_common.cache_load(
                {}, False, logging.WARNING, cache_dir=cache_dir, speakers={speaker_b}
            )
            self.assertIn(speaker_b, loaded)
            self.assertNotIn(speaker_a, loaded)

            generate_common.cache_save_incremental(
                {}, {speaker_b}, {speaker_a}, cache_dir=cache_dir, prune=True
            )
            reloaded = generate_common.cache_load(
                {}, False, logging.WARNING, cache_dir=cache_dir, speakers={speaker_a}
            )
            self.assertNotIn(speaker_a, reloaded)

    def test_find_complete_checks_both_plain_and_eq_entries(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            cache_dir = os.path.join(temporary_dir, ".cache")
            os.makedirs(cache_dir)
            generate_common.cache_save_key(
                generate_common.cache_key("Speaker A"),
                {
                    "Speaker A": {
                        "O1": {"v1": np.array([1.0]), "v1_eq": np.array([1.0])},
                        "O2": {"v2": np.array([2.0])},
                    }
                },
                cache_dir=cache_dir,
            )
            found = generate_common.cache_find_complete(
                cache_dir, {"Speaker A": {"v1": "O1", "v2": "O2", "v3": "O1"}}
            )
            self.assertEqual(found, {("Speaker A", "v1")})
            self.assertEqual(generate_common.cache_find_complete(cache_dir, {}), set())
            self.assertEqual(
                generate_common.cache_find_complete(
                    os.path.join(temporary_dir, "missing"), {"Speaker A": {"v1": "O1"}}
                ),
                set(),
            )

    def test_speaker_filter_matches_original_or_sanitized_only(self):
        self.assertTrue(generate_common._speaker_matches_filter("A|B", None))
        self.assertTrue(generate_common._speaker_matches_filter("A|B", {}))
        self.assertTrue(generate_common._speaker_matches_filter("A|B", {"origin": "ASR"}))
        self.assertTrue(generate_common._speaker_matches_filter("A|B", {"speaker": "A|B"}))
        self.assertTrue(generate_common._speaker_matches_filter("A|B", {"speaker": "A_B"}))
        self.assertFalse(generate_common._speaker_matches_filter("A|B", {"speaker": "Other"}))

    def test_small_load_reads_inline_without_a_pool(self):
        # Spawning a full worker pool to read a single shard stalls some
        # environments (a dozen fresh interpreters under pytest) and is
        # slower than reading the file directly; pin the inline fast path.
        with tempfile.TemporaryDirectory() as temporary_dir:
            cache_dir = os.path.join(temporary_dir, ".cache")
            os.makedirs(cache_dir)
            generate_common.cache_save_key(
                generate_common.cache_key("Speaker A"),
                {"Speaker A": {"O": {"v": np.array([1.0])}}},
                cache_dir=cache_dir,
            )

            def _no_pool(*args, **kwargs):
                msg = "pool created for a single shard"
                raise AssertionError(msg)

            with patch.object(generate_common.multiprocessing, "Pool", _no_pool):
                loaded = generate_common.cache_load_distributed(
                    {}, False, logging.WARNING, cache_dir=cache_dir
                )
            self.assertIn("Speaker A", loaded)

    def test_large_load_still_uses_one_pool(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            cache_dir = os.path.join(temporary_dir, ".cache")
            os.makedirs(cache_dir)
            speakers = [f"Speaker {i}" for i in range(4)]
            for i, speaker in enumerate(speakers):
                generate_common.cache_save_key(
                    generate_common.cache_key(speaker),
                    {speaker: {"O": {"v": np.array([float(i)])}}},
                    cache_dir=cache_dir,
                )

            created = []

            class _FakePool:
                def __init__(self, processes=None):
                    created.append(processes)

                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

                def map(self, func, items):
                    return [func(item) for item in items]

            with (
                patch.object(generate_common.multiprocessing, "cpu_count", return_value=2),
                patch.object(generate_common.multiprocessing, "Pool", _FakePool),
            ):
                loaded = generate_common.cache_load_distributed(
                    {}, False, logging.WARNING, cache_dir=cache_dir
                )
            # 4 shards > 1 worker: exactly one pool, results merged like pool.map.
            self.assertEqual(created, [1])
            for speaker in speakers:
                self.assertIn(speaker, loaded)


class TestGraphCacheCompleteness(unittest.TestCase):
    def test_requires_every_measurement_and_eq_variant(self):
        speakers = {
            "Test Speaker": {
                "measurements": {
                    "eac": {"origin": "ErinsAudioCorner"},
                    "vendor": {"origin": "Vendor"},
                }
            }
        }
        with patch.object(generate_graphs.metadata, "speakers_info", speakers):
            self.assertFalse(
                generate_graphs.speaker_cache_complete(
                    "Test Speaker", {"ErinsAudioCorner": {"eac": object()}}
                )
            )
            self.assertTrue(
                generate_graphs.speaker_cache_complete(
                    "Test Speaker",
                    {
                        "ErinsAudioCorner": {"eac": object(), "eac_eq": object()},
                        "Vendor": {"vendor": object(), "vendor_eq": object()},
                    },
                )
            )


if __name__ == "__main__":
    unittest.main()
