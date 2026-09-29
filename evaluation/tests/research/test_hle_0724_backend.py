import asyncio
import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from arex_v2.backends.research import command
from eval_unified import (
    build_parser,
    collect_hle_rerun_indices_and_copy_retained,
    hle_0724_call_stats,
    hle_result_meets_finish_confidence_threshold,
    parse_confidence_value,
    run_all,
    run_hle_per_case_outer_chain,
    run_one_hle_0724_sample,
)
from hle_0724_backend import (
    DEFAULT_HLE_HARNESS_DIR,
    DEFAULT_HLE_JUDGE_SCRIPT,
    HLE0724Backend,
    select_hle_0724_samples,
)
from unified_eval.types import DatasetSpec, EvalSample


class _FakeClient:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class _FakeAgentModule:
    def __init__(self):
        self.client = None
        self.last_args = None
        self.last_question = None

    def build_openai_client(self, args):
        self.client = _FakeClient()
        return self.client

    async def attempt_question(self, question, args):
        self.last_question = question
        self.last_args = args
        finish = (
            '<tool_call><function=finish><parameter=answer>answer</parameter>'
            '<parameter=evidences>[{"evidence":"fact","url":"url"}]</parameter>'
            '<parameter=confidence>91</parameter></function></tool_call>'
        )
        return {
            "id": question["id"],
            "content": "answer",
            "reasoning": "reasoning",
            "usage": {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
            "model_call_usage": [{"step": 0}],
            "model_usage_summary": {
                "model_calls": 1,
                "input_tokens": 10,
                "output_tokens": 2,
                "total_tokens": 12,
                "api_time": 0.1,
            },
            "steps": 1,
            "trajectory": [{"step": 0, "type": "finish"}],
            "context_management_steps": [],
            "messages": [{"role": "assistant", "content": finish}],
        }

    @staticmethod
    def parse_qwen_tool_calls(_content):
        return [{
            "function": "finish",
            "arguments": {
                "answer": "answer",
                "evidences": [{"evidence": "fact", "url": "url"}],
                "confidence": 91,
            },
        }]


class _FakeJudgeModule:
    def __init__(self):
        self.client = None
        self.last_prediction = None

    def build_client(self, _args):
        self.client = _FakeClient()
        return self.client

    @staticmethod
    def _is_local_endpoint(_base_url):
        return True

    async def add_judge_response(self, **kwargs):
        question = kwargs["question"]
        self.last_prediction = kwargs["predictions"][question["id"]]
        judged = dict(self.last_prediction)
        judged["judge_response"] = {
            "correct_answer": question["_answer"],
            "model_answer": "answer",
            "reasoning": "match",
            "correct": "yes",
            "confidence": 100,
            "judge_type": "external_hle_judge",
            "raw_judge_outputs": [],
            "response_truncated_for_judge": False,
        }
        return question["id"], judged


def _sample(idx=7):
    raw = {
        "id": f"id-{idx}",
        "question": "question",
        "image": "",
        "answer": "answer",
    }
    return EvalSample(
        dataset_name="HLE",
        sample_id=raw["id"],
        idx=idx,
        question=raw["question"],
        answer=raw["answer"],
        raw=raw,
    )


def _spec():
    return DatasetSpec(
        name="HLE",
        data_path="data.jsonl",
        data_format="jsonl",
        task_type="qa_multimodal",
        question_field="question",
        answer_field="answer",
        id_field="id",
        evaluation_backend="hle_0724",
    )


def _write_hle_data(root: Path) -> Path:
    path = root / "text_items.jsonl"
    path.write_text(
        json.dumps({"id": "id-0", "question": "question", "answer": "answer", "image": ""}) + "\n",
        encoding="utf-8",
    )
    return path


class HLE0724BackendTest(unittest.IsolatedAsyncioTestCase):
    def test_hle_call_stats_include_update_context(self):
        stats = hle_0724_call_stats({
            "model_usage_summary": {"model_calls": 3},
            "hle_trajectory": [
                {
                    "type": "update_context",
                    "tool": "update_context",
                    "context_tokens": 12,
                    "context_chars": 48,
                },
                {"type": "finish", "confidence": 91},
            ],
        })
        self.assertEqual(stats["llm_calls_total"], 3)
        self.assertEqual(stats["update_context_calls_total"], 1)
        self.assertEqual(stats["update_context_context_tokens_total"], 12)
        self.assertEqual(stats["update_context_context_chars_total"], 48)

    def test_hle_rerun_confidence_helpers(self):
        self.assertEqual(parse_confidence_value("91%"), 91.0)
        self.assertEqual(parse_confidence_value("confidence: 89.5"), 89.5)
        self.assertIsNone(parse_confidence_value(""))

        high_confidence = {
            "confidence": "91",
            "trajectory": [
                {
                    "role": "assistant",
                    "content": "<tool_call><function=finish></function></tool_call>",
                }
            ],
        }
        low_confidence = dict(high_confidence, confidence="89")
        native_high_confidence = {
            "confidence": "95%",
            "hle_0724": {
                "trajectory": [{"step": 42, "type": "finish"}],
            },
        }
        no_finish = {"confidence": "99", "trajectory": []}
        self.assertTrue(hle_result_meets_finish_confidence_threshold(high_confidence, 90))
        self.assertTrue(hle_result_meets_finish_confidence_threshold(native_high_confidence, 90))
        self.assertFalse(hle_result_meets_finish_confidence_threshold(low_confidence, 90))
        self.assertFalse(hle_result_meets_finish_confidence_threshold(no_finish, 90))

    def test_hle_rerun_indices_and_retained_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            dest = Path(tmp) / "dest"
            source.mkdir()
            dest.mkdir()
            cases = {
                "2026-08-20_00-00-00_row3": {
                    "confidence": "95",
                    "trajectory": [
                        {
                            "role": "assistant",
                            "content": "<tool_call><function=finish></function></tool_call>",
                        }
                    ],
                },
                "2026-08-20_00-00-01_row4": {
                    "confidence": "80",
                    "trajectory": [
                        {
                            "role": "assistant",
                            "content": "<tool_call><function=finish></function></tool_call>",
                        }
                    ],
                },
                "2026-08-20_00-00-02_row5": {
                    "confidence": "",
                    "trajectory": [],
                },
            }
            for dirname, data in cases.items():
                case_dir = source / dirname
                case_dir.mkdir()
                (case_dir / "temp.json").write_text(
                    json.dumps(data),
                    encoding="utf-8",
                )
                (case_dir / "temp_origin.json").write_text(
                    json.dumps({"origin": dirname}),
                    encoding="utf-8",
                )

            rerun_indices, stats = collect_hle_rerun_indices_and_copy_retained(
                str(source),
                str(dest),
                90,
                True,
            )

            self.assertEqual(rerun_indices, {4, 5})
            self.assertEqual(stats["retained_cases"], 1)
            self.assertEqual(stats["copied_cases"], 1)
            self.assertTrue((dest / "2026-08-20_00-00-00_row3" / "temp.json").is_file())
            self.assertFalse((dest / "2026-08-20_00-00-01_row4").exists())

    def test_selection_matches_original_random_sample(self):
        samples = [_sample(idx) for idx in range(100)]
        selected = select_hle_0724_samples(
            samples,
            0,
            20,
            None,
            0,
            1,
            set(),
            True,
            seed=125,
        )
        expected = random.Random(125).sample(list(range(100)), 20)
        self.assertEqual([sample.idx for sample in selected], expected)

    async def test_backend_uses_0724_defaults_and_exact_modules(self):
        agent = _FakeAgentModule()
        judge = _FakeJudgeModule()
        backend = HLE0724Backend(
            {
                "model": "model",
                "sdk_base_url": "http://agent/v1",
                "sdk_api_key": "agent-key",
                "judge_base_url": "http://judge/v1",
                "judge_api_key": "judge-key",
                "judge_model": "judge-model",
            },
            agent_module=agent,
            judge_module=judge,
        )
        with tempfile.TemporaryDirectory() as tmp:
            result = await backend.run(_sample(), tmp)
        self.assertEqual(agent.last_args.max_completion_tokens, 49152)
        self.assertEqual(agent.last_args.truncation_max_completion_tokens, 8192)
        self.assertEqual(agent.last_args.max_context_tokens, 200000)
        self.assertEqual(agent.last_args.max_total_tokens, 262144)
        self.assertEqual(agent.last_args.max_steps, 100)
        self.assertEqual(agent.last_args.temperature, 1.0)
        self.assertEqual(agent.last_args.top_p, 0.95)
        self.assertFalse(agent.last_args.enable_thinking)
        self.assertTrue(agent.last_args.enable_visit_fallback)
        self.assertTrue(agent.last_args.text_only)
        self.assertEqual(result["predicted"], "answer")
        self.assertEqual(result["confidence"], 91)
        self.assertTrue(result["full_credit"])
        self.assertEqual(judge.last_prediction["response"], "answer")
        await backend.close()
        self.assertTrue(agent.client.closed)
        self.assertTrue(judge.client.closed)

    async def test_backend_passes_whitelisted_prior_outer_state(self):
        agent = _FakeAgentModule()
        judge = _FakeJudgeModule()
        with tempfile.TemporaryDirectory() as tmp:
            prior_path = Path(tmp) / 'temp.json'
            prior_path.write_text(json.dumps({
                'predicted': 'prior answer',
                'confidence': 84,
                'evidence': [{'evidence': 'fact', 'url': 'url'}],
                'answer': 'SECRET_GOLD',
                'metadata': {'rationale': 'SECRET_RATIONALE'},
                'trajectory': [{'role': 'assistant', 'content': 'prior work'}],
                'hle_0724': {
                    'judge_response': {'reasoning': 'SECRET_JUDGE'},
                    'raw_prediction': {
                        'messages': [{'role': 'assistant', 'content': 'prior work'}],
                    },
                },
            }), encoding='utf-8')
            backend = HLE0724Backend(
                {
                    'model': 'model',
                    'sdk_base_url': 'http://agent/v1',
                    'sdk_api_key': 'agent-key',
                    'judge_base_url': 'http://judge/v1',
                    'judge_api_key': 'judge-key',
                    'judge_model': 'judge-model',
                    'hle_outer_round': 2,
                    'hle_outer_resume_paths': {7: str(prior_path)},
                },
                agent_module=agent,
                judge_module=judge,
            )
            await backend.run(_sample(), tmp)
            resume = agent.last_args.outer_resume
            self.assertEqual(resume['source_outer'], 1)
            self.assertEqual(resume['draft']['answer'], 'prior answer')
            self.assertEqual(resume['draft']['confidence'], 84)
            self.assertNotIn('SECRET_', json.dumps(resume))
            await backend.close()

    async def test_unified_row_directory_output(self):
        agent = _FakeAgentModule()
        judge = _FakeJudgeModule()
        backend = HLE0724Backend(
            {
                "model": "model",
                "sdk_base_url": "http://agent/v1",
                "sdk_api_key": "agent-key",
                "judge_base_url": "http://judge/v1",
                "judge_api_key": "judge-key",
                "judge_model": "judge-model",
            },
            agent_module=agent,
            judge_module=judge,
        )
        with tempfile.TemporaryDirectory() as tmp:
            await run_one_hle_0724_sample(
                _spec(),
                _sample(),
                {"save_path": tmp, "max_attempts": 1, "case_timeout_seconds": 0},
                backend,
                asyncio.Semaphore(1),
            )
            row_dirs = list(Path(tmp).glob("*_row7"))
            self.assertEqual(len(row_dirs), 1)
            temp = json.loads((row_dirs[0] / "temp.json").read_text())
            origin = json.loads((row_dirs[0] / "temp_origin.json").read_text())
        self.assertEqual(temp["evaluation_backend"], "hle_0724")
        self.assertEqual(temp["predicted"], "answer")
        self.assertEqual(temp["score"], 1.0)
        self.assertEqual(temp["trajectory"][0]["role"], "assistant")
        self.assertEqual(origin["token_usage"]["total_tokens"], 12)
        await backend.close()

    async def test_run_all_routes_hle_without_generic_tokenizer_or_agent(self):
        agent = _FakeAgentModule()
        judge = _FakeJudgeModule()

        def backend_factory(config):
            return HLE0724Backend(
                config,
                agent_module=agent,
                judge_module=judge,
            )

        with tempfile.TemporaryDirectory() as tmp:
            data_path = _write_hle_data(Path(tmp))
            args = build_parser().parse_args([
                "--datasets",
                "HLE",
                "--save_path",
                tmp,
                "--data_path",
                str(data_path),
                "--target_indices",
                "0",
                "--no-shuffle",
                "--model",
                "model",
                "--sdk_base_url",
                "http://agent/v1",
                "--sdk_api_key",
                "agent-key",
                "--judge_base_url",
                "http://judge/v1",
                "--judge_api_key",
                "judge-key",
                "--judge_model",
                "judge-model",
            ])
            with mock.patch("eval_unified.HLE0724Backend", side_effect=backend_factory), \
                    mock.patch("eval_unified.import_tokenizer") as import_tokenizer:
                await run_all(args)
            import_tokenizer.assert_not_called()
            row_dirs = list((Path(tmp) / "HLE").glob("*_row0"))
            self.assertEqual(len(row_dirs), 1)
            temp = json.loads((row_dirs[0] / "temp.json").read_text())
            self.assertEqual(temp["evaluation_backend"], "hle_0724")
            self.assertEqual(temp["score"], 1.0)
            run_metadata = json.loads((Path(tmp) / "HLE" / "run_metadata.json").read_text())
            self.assertEqual(run_metadata["git_commit"], run_metadata["git"]["commit"])
            self.assertEqual(run_metadata["evaluator_mode"], "direct")
            self.assertIn("data_checksum", run_metadata)
            self.assertEqual(temp["run_metadata"]["data_checksum"], run_metadata["data_checksum"])

    async def test_run_all_maps_selected_prior_outer_result_to_backend(self):
        agent = _FakeAgentModule()
        judge = _FakeJudgeModule()

        def backend_factory(config):
            return HLE0724Backend(
                config,
                agent_module=agent,
                judge_module=judge,
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_path = _write_hle_data(root)
            source_case = root / 'source' / 'HLE' / '2026-09-17_00-00-00_row0'
            source_case.mkdir(parents=True)
            source_case.joinpath('temp.json').write_text(json.dumps({
                'predicted': 'prior answer',
                'confidence': 80,
                'evidence': [],
                'trajectory': [{
                    'role': 'assistant',
                    'content': '<tool_call><function=finish></function></tool_call>',
                }],
            }), encoding='utf-8')
            args = build_parser().parse_args([
                '--datasets', 'HLE',
                '--save_path', str(root / 'output'),
                '--data_path', str(data_path),
                '--target_indices', '0', '--no-shuffle',
                '--model', 'model',
                '--sdk_base_url', 'http://agent/v1',
                '--sdk_api_key', 'agent-key',
                '--judge_base_url', 'http://judge/v1',
                '--judge_api_key', 'judge-key',
                '--judge_model', 'judge-model',
                '--hle-rerun-source-root', str(root / 'source'),
                '--hle-rerun-confidence-threshold', '95',
                '--hle-outer-review-resume', '--hle-outer-round', '2',
            ])
            with mock.patch('eval_unified.HLE0724Backend', side_effect=backend_factory):
                await run_all(args)
            self.assertEqual(agent.last_args.outer_round, 2)
            self.assertEqual(agent.last_args.outer_resume['draft']['answer'], 'prior answer')
            self.assertEqual(agent.last_args.outer_resume['source_outer'], 1)

    async def test_public_profile_resumes_unfinished_chain_and_publishes_only_final(self):
        seen = []
        interrupted = False

        class Agent(_FakeAgentModule):
            async def attempt_question(self, question, args):
                nonlocal interrupted
                seen.append(args.outer_round)
                if args.outer_round == 2 and not interrupted:
                    interrupted = True
                    raise asyncio.CancelledError()
                result = await super().attempt_question(question, args)
                result['accepted_finish'] = {
                    'answer': 'answer', 'evidences': [],
                    'confidence': 96 if args.outer_round == 2 else 80,
                }
                return result

        agent = Agent()

        def backend_factory(config):
            return HLE0724Backend(config, agent_module=agent, judge_module=_FakeJudgeModule())

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = _write_hle_data(root)
            argv, env = command(
                Path(__file__).resolve().parents[3], 'HLE', model='agent',
                base_url='http://agent.test/v1', judge_model='judge',
                judge_base_url='http://judge.test/v1', judge_api_key_env='JUDGE_API_KEY',
                data_path=str(data), save_path=str(root / 'output'), dry_run=True,
            )
            with mock.patch.dict('os.environ', env), \
                    mock.patch('eval_unified.HLE0724Backend', side_effect=backend_factory):
                args = build_parser().parse_args(argv[2:-1])
                # The public wrapper normally passes the input via its subprocess environment.
                args.data_path = str(data)
                with self.assertRaises(asyncio.CancelledError):
                    await run_all(args)
                self.assertFalse(list((root / 'output' / 'HLE').glob('*/temp.json')))
                self.assertEqual(len(list((root / 'output' / '_hle_outer' / 'outer1').rglob('temp.json'))), 1)
                await run_all(args)
                final_paths = list((root / 'output' / 'HLE').glob('*/temp.json'))
                self.assertEqual(len(final_paths), 1)
                final = json.loads(final_paths[0].read_text())
                self.assertEqual(final['hle_0724']['outer_round'], 2)
                self.assertEqual(final['confidence'], 96)
                self.assertEqual(seen, [1, 2, 2])
                await run_all(args)
                self.assertEqual(seen, [1, 2, 2])
            self.assertEqual(agent.last_args.max_completion_tokens, 16384)
            self.assertEqual(agent.last_args.max_context_tokens, 240000)
            self.assertEqual(agent.last_args.llm_call_max_retries, 5)
            self.assertEqual(agent.last_args.general_max_attempts, 10)
            self.assertEqual(agent.last_args.temperature, 1.0)
            self.assertTrue(agent.last_args.enable_thinking)
            self.assertTrue(agent.last_args.preserve_thinking)

    async def test_per_case_outer_chain_advances_without_batch_barrier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior_dir = root / 'outer1' / 'HLE' / 'source_row7'
            prior_dir.mkdir(parents=True)
            prior_path = prior_dir / 'temp.json'
            prior_path.write_text(json.dumps({
                'confidence': 80,
                'hle_0724': {'trajectory': [{'type': 'finish'}]},
            }), encoding='utf-8')
            seen = []

            async def fake_run(
                spec, sample, config, backend, semaphore, *,
                outer_resume_path=None, outer_round=None, use_semaphore=True,
            ):
                seen.append((outer_round, outer_resume_path, use_semaphore))
                case_dir = Path(config['save_path']) / f'case_row{sample.idx}'
                case_dir.mkdir(parents=True)
                path = case_dir / 'temp.json'
                path.write_text(json.dumps({
                    'confidence': 96 if outer_round == 3 else 80,
                    'hle_0724': {'trajectory': [{'type': 'finish'}]},
                }), encoding='utf-8')
                return str(path)

            config = {
                'hle_outer_resume_paths': {7: str(prior_path)},
                'hle_outer_round': 2,
                'hle_per_case_outer_max': 5,
                'hle_rerun_confidence_threshold': 95,
                'hle_per_case_outer_root': str(root / 'results'),
            }
            with mock.patch('eval_unified.run_one_hle_0724_sample', side_effect=fake_run):
                await run_hle_per_case_outer_chain(
                    _spec(), _sample(), config, mock.sentinel.backend,
                    asyncio.Semaphore(1),
                )

            self.assertEqual([item[0] for item in seen], [2, 3])
            self.assertEqual(seen[1][1], str(root / 'results' / 'outer2' / 'HLE' / 'case_row7' / 'temp.json'))
            self.assertTrue(all(item[2] is False for item in seen))

    async def test_per_case_outer_chain_caps_each_outer_by_remaining_total_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prior_dir = root / 'outer1' / 'HLE' / 'source_row7'
            prior_dir.mkdir(parents=True)
            prior_path = prior_dir / 'temp.json'
            prior_path.write_text(json.dumps({
                'confidence': 80,
                'hle_0724': {
                    'trajectory': [{'type': 'finish'}],
                    'model_usage_summary': {'model_calls': 4},
                },
            }), encoding='utf-8')
            seen_max_steps = []

            async def fake_run(
                spec, sample, config, backend, semaphore, *,
                outer_resume_path=None, outer_round=None, use_semaphore=True,
            ):
                seen_max_steps.append(config['hle_max_steps'])
                case_dir = Path(config['save_path']) / f'case_row{sample.idx}'
                case_dir.mkdir(parents=True)
                path = case_dir / 'temp.json'
                path.write_text(json.dumps({
                    'confidence': 80,
                    'hle_0724': {
                        'trajectory': [{'type': 'finish'}],
                        'model_usage_summary': {'model_calls': config['hle_max_steps']},
                    },
                }), encoding='utf-8')
                return str(path)

            config = {
                'hle_outer_resume_paths': {7: str(prior_path)},
                'hle_outer_round': 2,
                'hle_per_case_outer_max': 10,
                'hle_rerun_confidence_threshold': 95,
                'hle_max_steps': 300,
                'hle_per_case_total_max_steps': 6,
                'hle_per_case_outer_root': str(root / 'results'),
            }
            with mock.patch('eval_unified.run_one_hle_0724_sample', side_effect=fake_run):
                await run_hle_per_case_outer_chain(
                    _spec(), _sample(), config, mock.sentinel.backend,
                    asyncio.Semaphore(1),
                )

            self.assertEqual(seen_max_steps, [2])

    async def test_per_case_chain_waits_for_only_its_missing_outer1_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'outer1' / 'HLE'
            source.mkdir(parents=True)
            prior_dir = source / 'late_row7'
            prior_path = prior_dir / 'temp.json'
            observed = []

            async def publish_outer1(_seconds):
                prior_dir.mkdir()
                prior_path.write_text(json.dumps({
                    'confidence': 96,
                    'hle_0724': {'trajectory': [{'type': 'finish'}]},
                }), encoding='utf-8')

            async def should_not_run(*args, **kwargs):
                observed.append('ran')
                raise AssertionError('high-confidence late outer1 must stop before outer2')

            config = {
                'hle_outer_resume_paths': {},
                'hle_outer_resume_source_root': str(source),
                'hle_outer_source_poll_seconds': 0.01,
                'hle_outer_round': 2,
                'hle_per_case_outer_max': 5,
                'hle_rerun_confidence_threshold': 95,
                'hle_per_case_outer_root': str(root / 'results'),
            }
            with mock.patch('eval_unified.asyncio.sleep', side_effect=publish_outer1), \
                    mock.patch('eval_unified.run_one_hle_0724_sample', side_effect=should_not_run):
                await run_hle_per_case_outer_chain(
                    _spec(), _sample(), config, mock.sentinel.backend,
                    asyncio.Semaphore(1),
                )

            self.assertEqual(observed, [])

    async def test_per_case_chain_fills_missing_outer1_under_shared_semaphore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'outer1' / 'HLE'
            source.mkdir(parents=True)
            seen = []
            semaphore = asyncio.Semaphore(1)

            async def fake_run(
                spec, sample, config, backend, passed_semaphore, *,
                outer_resume_path=None, outer_round=None, use_semaphore=True,
            ):
                self.assertIs(passed_semaphore, semaphore)
                self.assertTrue(semaphore.locked())
                seen.append({
                    'outer': outer_round,
                    'save_path': config['save_path'],
                    'resume': outer_resume_path,
                    'use_semaphore': use_semaphore,
                })
                case_dir = Path(config['save_path']) / f'case_row{sample.idx}'
                case_dir.mkdir(parents=True, exist_ok=True)
                path = case_dir / 'temp.json'
                path.write_text(json.dumps({
                    'confidence': 96 if outer_round == 2 else 80,
                    'hle_0724': {
                        'trajectory': [{'type': 'finish'}],
                        'model_usage_summary': {'model_calls': 4},
                    },
                }), encoding='utf-8')
                return str(path)

            config = {
                'hle_outer_resume_paths': {},
                'hle_outer_resume_source_root': str(source),
                'hle_per_case_fill_missing_outer1': True,
                'hle_outer_round': 2,
                'hle_per_case_outer_max': 5,
                'hle_rerun_confidence_threshold': 95,
                'hle_max_steps': 300,
                'hle_per_case_total_max_steps': 1500,
                'hle_per_case_outer_root': str(root / 'results'),
            }
            with mock.patch(
                'eval_unified.run_one_hle_0724_sample', side_effect=fake_run
            ):
                await run_hle_per_case_outer_chain(
                    _spec(), _sample(), config, mock.sentinel.backend, semaphore,
                )

            self.assertEqual([item['outer'] for item in seen], [1, 2])
            self.assertEqual(seen[0]['save_path'], str(source))
            self.assertIsNone(seen[0]['resume'])
            self.assertEqual(
                seen[1]['save_path'],
                str(root / 'results' / 'outer2' / 'HLE'),
            )
            self.assertEqual(seen[1]['resume'], seen[0]['save_path'] + '/case_row7/temp.json')
            self.assertTrue(all(not item['use_semaphore'] for item in seen))

    def test_cli_defaults_match_0724_command(self):
        args = build_parser().parse_args([])
        root = Path(__file__).resolve().parents[2] / "research_eval"
        self.assertTrue(Path(DEFAULT_HLE_HARNESS_DIR).is_relative_to(root))
        self.assertTrue(Path(DEFAULT_HLE_JUDGE_SCRIPT).is_relative_to(root))
        self.assertEqual(args.hle_harness_dir, DEFAULT_HLE_HARNESS_DIR)
        self.assertEqual(args.hle_judge_script, DEFAULT_HLE_JUDGE_SCRIPT)
        self.assertEqual(args.hle_seed, 125)
        self.assertEqual(args.hle_num_samples, 200)
        self.assertEqual(args.hle_max_completion_tokens, 49152)
        self.assertEqual(args.hle_truncation_max_completion_tokens, 8192)
        self.assertEqual(args.hle_max_context_tokens, 200000)
        self.assertEqual(args.hle_max_total_tokens, 262144)
        self.assertEqual(args.hle_max_steps, 100)
        self.assertEqual(args.hle_tool_call_regen_max_retries, 20)
        self.assertFalse(args.hle_enable_thinking)
        self.assertFalse(args.hle_outer_review_resume)
        self.assertEqual(args.hle_outer_round, 1)
        self.assertFalse(args.hle_per_case_fill_missing_outer1)


if __name__ == "__main__":
    unittest.main()
