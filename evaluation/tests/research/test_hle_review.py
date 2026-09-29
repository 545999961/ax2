import copy
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from hle_0724_backend import HLE0724Backend, _extract_finish_fields, _load_module
from eval_unified import build_parser, hle_0724_call_stats
from hle_0724_vendor import hle_review


def finish(answer='2', confidence='92'):
    return (
        '<tool_call><function=finish><parameter=answer>' + answer + '</parameter>'
        '<parameter=evidences>[]</parameter><parameter=confidence>' + confidence +
        '</parameter></function></tool_call>'
    )


def review(assessment='unresolved'):
    return json.dumps({
        'assessment': assessment,
        'supported_work': ['The setup is consistent with the question.'],
        'issues': [] if assessment == 'no_specific_issue' else [{
            'step': 'Final arithmetic', 'kind': 'uncertainty',
            'reason': 'No substitution check is shown.', 'check': 'Substitute 2 into the equation.',
        }],
        'next_actions': [] if assessment == 'no_specific_issue' else ['Substitute the result.'],
    })


class HLEReviewTest(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3] / 'src' / 'research_eval' / 'hle_0724_vendor'
        tokenizer = SimpleNamespace(encode=lambda text: text.split())
        with mock.patch('transformers.AutoTokenizer.from_pretrained', return_value=tokenizer), \
                mock.patch('openai.AsyncOpenAI'):
            cls.agent = _load_module('hle_agent_review_test', root / 'run_evaluation_kimi_agent.py', import_root=root)

    async def run_sequence(self, outputs, **options):
        args = SimpleNamespace(
            model='test-model', enable_visit_fallback=True, max_steps=10,
            max_context_tokens=200000, max_completion_tokens=1024,
            truncation_max_completion_tokens=512, max_total_tokens=262144,
            tool_call_regen_max_retries=0, temperature=0.9, top_p=0.93,
            top_k=40, min_p=0.0, presence_penalty=0.0, repetition_penalty=1.08,
            enable_thinking=True, preserve_thinking=True,
            enable_confidence_review=True, review_threshold=95,
            review_middle_threshold=90, review_max_rounds=2, review_max_tokens=512,
        )
        args.__dict__.update(options)
        requests = []

        async def create(**kwargs):
            requests.append(copy.deepcopy(kwargs))
            output = outputs[len(requests) - 1]
            if isinstance(output, Exception):
                raise output
            return SimpleNamespace(
                usage=SimpleNamespace(model_dump_json=lambda: json.dumps({
                    'prompt_tokens': 20, 'completion_tokens': 10, 'total_tokens': 30,
                })),
                choices=[SimpleNamespace(
                    finish_reason='stop',
                    message=SimpleNamespace(content=output, reasoning_content='solution reasoning'),
                )],
            )

        namespace = {}
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(self.agent, 'client', fake_client), \
                mock.patch.object(self.agent, 'create_python_interpreter', return_value=namespace), \
                mock.patch.object(self.agent, '_shutdown_python_interpreter'), \
                mock.patch.object(self.agent, 'execute_tool_async', new_callable=mock.AsyncMock, return_value='2') as tool:
            args.output = str(Path(tmp) / 'out.jsonl')
            result = await self.agent.run_agent({
                'id': 'test', 'question': 'Solve x + 1 = 3.',
                'answer': 'SECRET_ANSWER_KEY', 'rationale': 'SECRET_RATIONALE',
                'metadata': {'judge_response': 'SECRET_JUDGE'},
            }, args)
            for call in tool.call_args_list:
                self.assertIs(call.args[2], namespace)
        return result, requests

    async def test_review_then_compute_then_finish(self):
        code = '<tool_call><function=code_interpreter><parameter=code>2 + 1</parameter></function></tool_call>'
        result, requests = await self.run_sequence([finish(), review(), code, finish(confidence='97')])
        self.assertEqual(result['accepted_finish']['confidence'], 97)
        self.assertEqual(result['model_usage_summary']['model_calls'], 4)
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual([event['type'] for event in result['trajectory']], ['finish_draft', 'review', 'tool_call', 'finish'])
        self.assertEqual(len(requests[1]['messages']), 2)
        self.assertIn(hle_review.MID_GUIDANCE.strip(), requests[1]['messages'][0]['content'])
        self.assertNotIn('SECRET_', json.dumps(requests[1]))
        self.assertIn('Review feedback:', requests[2]['messages'][-1]['content'])
        self.assertEqual(result['confidence_review']['drafts'][0]['confidence'], 92)
        stats = hle_0724_call_stats({
            'hle_trajectory': result['trajectory'],
            'model_usage_summary': result['model_usage_summary'],
        })
        self.assertEqual(stats['review_calls_total'], 1)
        self.assertEqual(stats['llm_calls_total'], 4)

    async def test_outer_resume_reviews_prior_attempt_before_new_solver_call(self):
        outer_resume = {
            'source_result_path': '/tmp/outer1/row7/temp.json',
            'source_outer': 1,
            'draft': {
                'answer': 'previous answer',
                'confidence': 82,
                'evidences': [{'evidence': 'prior evidence', 'url': 'https://example.test'}],
            },
            'messages': [
                {'role': 'assistant', 'content': 'prior derivation'},
                {'role': 'user', 'content': '<tool_response>prior tool output</tool_response>'},
            ],
        }
        result, requests = await self.run_sequence(
            [review(), finish(answer='3', confidence='97')],
            outer_resume=outer_resume,
            outer_round=2,
            enable_confidence_review=False,
        )
        self.assertEqual(len(requests), 2)
        self.assertIn('previous answer', requests[0]['messages'][1]['content'])
        self.assertNotIn('SECRET_', json.dumps(requests[0]))
        self.assertIn('This is outer attempt 2.', requests[1]['messages'][-1]['content'])
        self.assertIn('previous answer', requests[1]['messages'][-1]['content'])
        self.assertEqual(
            [event['type'] for event in result['trajectory']],
            ['outer_review', 'finish'],
        )
        self.assertEqual(result['model_usage_summary']['model_calls'], 2)
        self.assertEqual(result['outer_resume']['source_outer'], 1)
        self.assertEqual(result['accepted_finish']['answer'], '3')

    async def test_high_confidence_and_disabled_review(self):
        for confidence, enabled in [('95', True), ('55', False)]:
            result, requests = await self.run_sequence([finish(confidence=confidence)], enable_confidence_review=enabled)
            self.assertEqual(len(requests), 1)
            self.assertFalse(result['confidence_review']['reviews'])

    async def test_two_reviews_may_retain_same_low_confidence_answer(self):
        result, requests = await self.run_sequence([
            finish(confidence='80'), review('no_specific_issue'),
            finish(confidence='80'), review('no_specific_issue'), finish(confidence='80'),
        ])
        self.assertEqual(len(requests), 5)
        self.assertIn(hle_review.LOW_GUIDANCE.strip(), requests[1]['messages'][0]['content'])
        self.assertEqual(result['confidence_review']['stop_reason'], 'review_limit')
        self.assertEqual(result['accepted_finish']['confidence'], 80)
        self.assertEqual(result['content'], '2')

    async def test_shared_budget_restores_last_valid_draft(self):
        result, requests = await self.run_sequence([
            finish(), review(), 'no tool', finish(answer='bad', confidence=''),
        ], max_steps=4)
        self.assertEqual(len(requests), 4)
        self.assertEqual(result['model_usage_summary']['model_calls'], 4)
        self.assertEqual(result['content'], '2')
        self.assertTrue(result['confidence_review']['used_saved_finish'])
        self.assertEqual(result['confidence_review']['stop_reason'], 'max_steps_exceeded')
        self.assertEqual(_extract_finish_fields(self.agent, result), ([], 92))
        self.assertIn('final model call', requests[-1]['messages'][-1]['content'])

    async def test_insufficient_budget_does_not_start_review(self):
        result, requests = await self.run_sequence([finish()], max_steps=3)
        self.assertEqual(len(requests), 1)
        self.assertEqual(result['confidence_review']['stop_reason'], 'insufficient_budget')

    async def test_bad_review_and_api_failure_are_recorded(self):
        for bad in ['invalid review text', RuntimeError('review unavailable')]:
            result, requests = await self.run_sequence([finish(), bad, finish(confidence='96')])
            self.assertEqual(len(requests), 3)
            self.assertIn('error', result['confidence_review']['reviews'][0])
            self.assertIn('no usable feedback', requests[2]['messages'][-1]['content'])
            self.assertEqual(result['accepted_finish']['confidence'], 96)

    async def test_invalid_confidence_cannot_trigger_review(self):
        result, requests = await self.run_sequence([finish(confidence=''), finish(confidence='100')])
        self.assertEqual(len(requests), 2)
        self.assertFalse(result['confidence_review']['reviews'])

    def test_payload_marks_partial_history_and_prompt_rendering(self):
        messages = hle_review.build_review_messages(
            {'question': 'Q', 'answer': 'SECRET'},
            {'answer': 'A', 'confidence': 92},
            [{'role': 'user', 'content': 'old' * 500}], max_chars=40,
        )
        data = json.loads(messages[1]['content'])
        self.assertTrue(data['trajectory_is_partial'])
        self.assertEqual(len(data['trajectory_text']), 40)
        self.assertNotIn('SECRET', messages[1]['content'])
        for name in (
            'SYSTEM_PROMPT', 'MID_GUIDANCE', 'LOW_GUIDANCE',
            'HANDOFF_PROMPT', 'OUTER_HANDOFF_PROMPT',
        ):
            prompt = getattr(hle_review, name)
            self.assertFalse(prompt.startswith('\n'))
            self.assertTrue(all(not line.startswith('    ') for line in prompt.splitlines()))

    def test_feedback_validation_rejects_contradictory_assessment(self):
        data = json.loads(review())
        data['assessment'] = 'no_specific_issue'
        with self.assertRaises(ValueError):
            hle_review.parse_review(json.dumps(data))
        data['assessment'] = 'error_found'
        with self.assertRaises(ValueError):
            hle_review.parse_review(json.dumps(data))

    def test_cli_review_settings_reach_agent(self):
        config = build_parser().parse_args([
            '--hle-enable-confidence-review', '--hle-review-threshold', '96',
            '--hle-review-middle-threshold', '85', '--hle-review-max-rounds', '1',
            '--hle-review-max-tokens', '2048',
        ])
        backend = object.__new__(HLE0724Backend)
        backend.harness_dir = Path(config.hle_harness_dir)
        backend.config = vars(config)
        args = backend._build_agent_args('/tmp/not_written.jsonl')
        self.assertTrue(args.enable_confidence_review)
        self.assertEqual((args.review_threshold, args.review_middle_threshold), (96, 85))
        self.assertEqual(args.review_max_rounds, 1)
        self.assertEqual(args.review_max_tokens, 2048)
        self.assertEqual(args.max_steps, 100)


if __name__ == '__main__':
    unittest.main()
