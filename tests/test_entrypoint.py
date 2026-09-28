from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from arex_v2.backends.research import command
from arex_v2.datasets import canonical_name, dataset_paths, path_is_ready


ROOT = Path(__file__).resolve().parents[1]


class DatasetSelectionTests(unittest.TestCase):
    def test_names_are_case_insensitive_and_keep_canonical_spelling(self) -> None:
        self.assertEqual(canonical_name("browsecomp"), "BrowseComp")
        self.assertEqual(canonical_name("  hle "), "HLE")
        self.assertEqual(canonical_name("deepsearchqa"), "DeepSearch-QA")
        self.assertEqual(canonical_name("xbench_deepsearch_2510"), "xBench-DeepSearch-2510")

    def test_vendor_dataset_paths_are_discovered_from_their_config(self) -> None:
        paths = dataset_paths(ROOT / "data", ["MoNaCo"])
        self.assertIn("MoNaCo", paths)
        self.assertTrue(paths["MoNaCo"].endswith("vendor/research/datasets/MoNaCo/execution_traces"))

    def test_directory_dataset_is_a_valid_input_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "trace.json").write_text("{}", encoding="utf-8")
            self.assertTrue(path_is_ready(temp))

    def test_dry_run_only_needs_dataset_selection(self) -> None:
        args, env = command(ROOT, "BrowseComp", num_tasks=1, dry_run=True)
        self.assertIn("--datasets", args)
        self.assertIn("BrowseComp", args)
        self.assertTrue(args[-1] == "--dry-run")
        self.assertNotIn("MODEL_API_KEY", env.get("AREX_SDK_API_KEY", ""))

    def test_real_command_checks_prepared_data_before_spawning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data_root = Path(temp)
            dataset_file = data_root / "BrowseComp" / "browse_comp_test_set.csv"
            dataset_file.parent.mkdir()
            dataset_file.write_text("problem,answer,canary\nquestion,answer,key\n", encoding="utf-8")
            old_key = os.environ.get("MODEL_API_KEY")
            os.environ["MODEL_API_KEY"] = "test-only"
            try:
                args, env = command(
                    ROOT,
                    "BrowseComp",
                    data_root=str(data_root),
                    model="test-model",
                    tokenizer_path="test-tokenizer",
                    num_tasks=1,
                )
            finally:
                if old_key is None:
                    os.environ.pop("MODEL_API_KEY", None)
                else:
                    os.environ["MODEL_API_KEY"] = old_key
            self.assertIn("--datasets", args)
            self.assertIn(str(dataset_file), env["AREX_DATA_PATHS"])


if __name__ == "__main__":
    unittest.main()
