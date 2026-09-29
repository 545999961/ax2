from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0, str(ROOT / "evaluation"))

from arex_v2.backends.research import command
from arex_v2.datasets import canonical_name, dataset_paths, path_is_ready


class DatasetSelectionTests(unittest.TestCase):
    def test_names_are_case_insensitive_and_keep_canonical_spelling(self) -> None:
        self.assertEqual(canonical_name("browsecomp"), "BrowseComp")
        self.assertEqual(canonical_name("  hle "), "HLE")
        self.assertEqual(canonical_name("deepsearchqa"), "DeepSearch-QA")
        self.assertEqual(canonical_name("gaia"), "GAIA-2023-validation-text-103")

    def test_core_dataset_paths_are_discovered_from_their_config(self) -> None:
        paths = dataset_paths(ROOT / "data" / "files", ["BrowseComp"])
        self.assertIn("BrowseComp", paths)
        self.assertTrue(paths["BrowseComp"].endswith("data/files/BrowseComp/browse_comp_test_set.csv"))

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
            old_judge_key = os.environ.get("JUDGE_API_KEY")
            os.environ["MODEL_API_KEY"] = "test-only"
            os.environ["JUDGE_API_KEY"] = "judge-only"
            try:
                args, env = command(
                    ROOT,
                    "BrowseComp",
                    data_root=str(data_root),
                    model="test-model",
                    tokenizer_path="test-tokenizer",
                    judge_model="test-judge",
                    judge_base_url="http://judge.test/v1",
                    judge_api_key_env="JUDGE_API_KEY",
                    num_tasks=1,
                )
            finally:
                if old_key is None:
                    os.environ.pop("MODEL_API_KEY", None)
                else:
                    os.environ["MODEL_API_KEY"] = old_key
                if old_judge_key is None:
                    os.environ.pop("JUDGE_API_KEY", None)
                else:
                    os.environ["JUDGE_API_KEY"] = old_judge_key
            self.assertIn("--datasets", args)
            self.assertIn(str(dataset_file), env["AREX_DATA_PATHS"])

    def test_refine_equal_profile_expands_shared_reference_settings(self) -> None:
        args, env = command(
            ROOT,
            "BrowseComp",
            model="model",
            base_url="http://model.test/v1",
            api_key_env="MODEL_API_KEY",
            tokenizer_path="tokenizer",
            judge_model="judge",
            judge_base_url="http://judge.test/v1",
            judge_api_key_env="JUDGE_API_KEY",
            num_tasks=3,
            dry_run=True,
        )
        rendered = " ".join(args)
        for fragment in (
            "--mode refine_summary",
            "--concurrency_limit 1",
            "--refine_summary_max_outer_rounds 10",
            "--refine_summary_max_llm_calls 300",
            "--refine_summary_max_total_llm_calls 1500",
            "--enable_confidence_tiered_review",
            "--agent_temperature 1.0",
            "--max_response_tokens 16384",
            "--llm_call_max_retries 5",
            "--summary_model model",
            "--judge-mode offical",
        ):
            self.assertIn(fragment, rendered)
        self.assertEqual(env["AREX_SUMMARY_API_KEY"], env.get("MODEL_API_KEY", ""))

    def test_hle_profile_uses_same_generation_values_and_outer_budget(self) -> None:
        args, _ = command(
            ROOT,
            "HLE",
            model="model",
            base_url="http://model.test/v1",
            tokenizer_path="",
            judge_model="judge",
            judge_base_url="http://judge.test/v1",
            judge_api_key_env="JUDGE_API_KEY",
            num_tasks=1,
            dry_run=True,
        )
        rendered = " ".join(args)
        for fragment in (
            "--mode direct",
            "--hle-max-steps 300",
            "--hle-per-case-outer-max 10",
            "--hle-per-case-total-max-steps 1500",
            "--hle-temperature 1.0",
            "--hle-top-p 0.95",
            "--hle-top-k 20",
            "--hle-tool-call-regen-max-retries 20",
            "--hle-llm-call-max-retries 5",
            "--hle-general-max-attempts 10",
        ):
            self.assertIn(fragment, rendered)

    def test_core_datasets_share_profile_and_allow_explicit_concurrency(self) -> None:
        for dataset in ("BrowseComp", "GAIA-2023-validation-text-103", "DeepSearch-QA"):
            with self.subTest(dataset=dataset):
                args, _ = command(ROOT, dataset, concurrency=2, dry_run=True)
                self.assertEqual(args[args.index("--concurrency_limit") + 1], "2")
                self.assertEqual(args.count("--concurrency_limit"), 1)
                self.assertIn("--enable_confidence_tiered_review", args)
        args, _ = command(ROOT, ["BrowseComp", "HLE"], dry_run=True)
        self.assertIn("--hle-per-case-outer-max", args)
        with self.assertRaisesRegex(ValueError, "Unknown research dataset"):
            command(ROOT, ["BrowseComp", "RemovedDataset"], dry_run=True)

    def test_summary_uses_agent_credentials_and_judge_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {
            "MODEL_API_KEY": "agent-only", "JUDGE_API_KEY": "judge-only",
        }):
            data = Path(tmp, "input.csv")
            data.write_text("problem,answer\nq,a\n", encoding="utf-8")
            options = dict(model="model", base_url="http://agent.test/v1",
                           tokenizer_path="tokenizer", data_path=str(data))
            with self.assertRaisesRegex(ValueError, "externally specified judge"):
                command(ROOT, "BrowseComp", **options)
            args, env = command(ROOT, "BrowseComp", **options, judge_model="judge",
                                judge_base_url="http://judge.test/v1", judge_api_key_env="JUDGE_API_KEY")
            self.assertEqual(env["AREX_SUMMARY_API_KEY"], "agent-only")
            self.assertEqual(env["AREX_JUDGE_API_KEY"], "judge-only")
            self.assertNotIn("agent-only", " ".join(args))
            self.assertNotIn("judge-only", " ".join(args))
            with self.assertRaisesRegex(ValueError, "summary override"):
                command(ROOT, "BrowseComp", **options, summary_model="other", dry_run=True)


if __name__ == "__main__":
    unittest.main()
