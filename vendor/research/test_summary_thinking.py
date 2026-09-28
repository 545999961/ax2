import types
import unittest

from Agent_no_subagent import MainAgent
from dataset_configs.BrowseComp.prompt import PROMPT_BUNDLE
from eval_unified import build_parser
from local_search import summarize


class RecordingCompletions:
    def __init__(self):
        self.requests = []

    async def create(self, **kwargs):
        self.requests.append(kwargs)
        message = types.SimpleNamespace(content='{"evidence":"fact","summary":"result"}')
        return types.SimpleNamespace(choices=[types.SimpleNamespace(message=message)])


class RecordingClient:
    def __init__(self):
        self.completions = RecordingCompletions()
        self.chat = types.SimpleNamespace(completions=self.completions)


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(str(text))


class SummaryThinkingTest(unittest.IsolatedAsyncioTestCase):
    async def _request_for(self, setting):
        client = RecordingClient()
        result = await summarize(
            client,
            "summary-model",
            [{"role": "user", "content": "summarize"}],
            summary_enable_thinking=setting,
        )
        self.assertEqual(result["summary"], "result")
        self.assertEqual(len(client.completions.requests), 1)
        return client.completions.requests[0]

    async def test_explicitly_disables_summary_thinking(self):
        request = await self._request_for(False)

        self.assertEqual(
            request["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": False}},
        )

    async def test_explicitly_enables_summary_thinking(self):
        request = await self._request_for(True)

        self.assertEqual(
            request["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": True}},
        )

    async def test_unset_preserves_server_default(self):
        request = await self._request_for(None)

        self.assertNotIn("extra_body", request)

    async def test_summary_function_defaults_to_thinking(self):
        client = RecordingClient()
        await summarize(
            client,
            "summary-model",
            [{"role": "user", "content": "summarize"}],
        )

        self.assertEqual(
            client.completions.requests[0]["extra_body"],
            {"chat_template_kwargs": {"enable_thinking": True}},
        )

    def test_cli_defaults_to_agent_and_summary_thinking(self):
        args = build_parser().parse_args([])

        self.assertTrue(args.enable_thinking)
        self.assertTrue(args.summary_enable_thinking)
        self.assertTrue(args.enable_visit_fallback)

    def test_cli_can_disable_agent_and_summary_thinking(self):
        args = build_parser().parse_args(
            ["--disable-thinking", "--summary-disable-thinking"]
        )

        self.assertFalse(args.enable_thinking)
        self.assertFalse(args.summary_enable_thinking)

    def test_cli_can_disable_visit_fallback(self):
        args = build_parser().parse_args(["--disable-visit-fallback"])

        self.assertFalse(args.enable_visit_fallback)

    def test_cli_can_run_missing_confidence_resume_cases_from_scratch(self):
        default_args = build_parser().parse_args([])
        enabled_args = build_parser().parse_args(
            ["--confidence-outer-resume-missing-from-scratch"]
        )

        self.assertFalse(default_args.confidence_outer_resume_missing_from_scratch)
        self.assertTrue(enabled_args.confidence_outer_resume_missing_from_scratch)

    def test_agent_defaults_to_explicit_qwen_thinking(self):
        agent = MainAgent(
            {
                "model": "Qwen3.5-4B",
                "context_limit_strategy": "refine_summary",
                "tool_names": [
                    "search",
                    "visit",
                    "update_context",
                    "finish",
                ],
                "prompt_bundle": PROMPT_BUNDLE,
                "max_tokens": 240000,
            },
            object(),
            object(),
            CharacterTokenizer(),
        )

        payload = agent._build_payload(agent.messages)

        self.assertTrue(agent.enable_thinking)
        self.assertTrue(
            payload["extra_body"]["chat_template_kwargs"]["enable_thinking"]
        )


if __name__ == "__main__":
    unittest.main()
