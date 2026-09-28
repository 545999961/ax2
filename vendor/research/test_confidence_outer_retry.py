import copy
import json
import unittest

from Agent_no_subagent import MainAgent
from eval_unified import confidence_outer_one_elapsed_seconds


class CharacterTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(text)


class ScriptedRefineSummaryAgent(MainAgent):
    def __init__(self, results, reviews=None, enabled=True):
        self.results = list(results)
        self.reviews = list(reviews or [])
        self.enable_confidence_outer_retry = enabled
        self.enable_confidence_tiered_review = False
        self.context_limit_strategy = "refine_summary"
        self.confidence_outer_retry_threshold = 95.0
        self.confidence_tiered_review_middle_threshold = 90.0
        self.confidence_outer_retry_meta = {}
        self.refine_summary_max_outer_rounds = len(self.results)
        self.refine_summary_max_total_llm_calls = 0
        self.refine_summary_outer_round = 0
        self.refine_summary_train_segments = []
        self.refine_summary_update_segments = []
        self.messages = []
        self.origin_messages = []
        self.step_feedback = []
        self.current_tokens = 0
        self.llm_timing_records = []
        self.review_calls = 0
        self.review_confidences = []
        self.transitions = []

    def _format_initial_user_prompt(self, question):
        return question

    def count_message_tokens(self, message):
        return len(str(message))

    def append_message(self, message, info=None):
        self.messages.append(copy.deepcopy(message))
        self.origin_messages.append(copy.deepcopy(message))
        self.step_feedback.append(info)

    def save_initial_state(self):
        self.initial_messages = copy.deepcopy(self.messages)

    def _reset_major_round_call_stats(self):
        pass

    def _note_current_tokens(self):
        pass

    def _log(self, message):
        pass

    def append_origin_event(self, event_type, content, **metadata):
        self.origin_messages.append(
            {"role": "event", "event_type": event_type, "content": content, **metadata}
        )

    def reset_to_initial_prompt(self, data_idx=None):
        self.messages = copy.deepcopy(self.initial_messages)
        self.step_feedback = [None] * len(self.messages)

    async def _run_refine_summary_inner(self, data):
        self.llm_timing_records.append({"type": "solver"})
        result = self.results[self.refine_summary_outer_round - 1]
        self.messages.append(
            {
                "role": "assistant",
                "content": f"outer-{self.refine_summary_outer_round}",
            }
        )
        self.step_feedback.append("finish" if result is not None else "no_finish")
        self.current_tokens = self.refine_summary_outer_round * 10
        return result

    async def _review_confidence_outer_trajectory(self, data, confidence_value=None):
        self.llm_timing_records.append({"type": "reviewer"})
        self.review_calls += 1
        self.review_confidences.append(confidence_value)
        self.last_confidence_outer_review = {"review_policy": "scripted"}
        return copy.deepcopy(self.reviews.pop(0))

    def _prepare_confidence_outer_next_round(self, decision, data_idx, next_outer_round):
        transition = "refine" if decision["trajectory_has_future_value"] == 1 else "restart"
        self.transitions.append(transition)
        self.reset_to_initial_prompt(data_idx=data_idx)
        if transition == "refine":
            self.messages.append(
                {
                    "role": "user",
                    "content": decision["information_to_keep"],
                }
            )
            self.step_feedback.append("refine_handoff")
        return transition


def review(mode, keep="", problems="", focus=""):
    return {
        "trajectory_has_future_value": mode,
        "information_to_keep": keep,
        "problems_to_focus": problems,
        "next_round_focus": focus,
    }


class ConfidenceOuterRetryTest(unittest.IsolatedAsyncioTestCase):
    async def test_cross_outer_total_budget_stops_before_unfunded_transition(self):
        agent = ScriptedRefineSummaryAgent(
            [("first", "", "70%"), ("second", "", "80%"), ("third", "", "99%")],
            reviews=[review(0), review(0)],
        )
        agent.refine_summary_max_total_llm_calls = 3

        result = await agent._run_refine_summary({"idx": 0, "problem": "question"})

        self.assertEqual(result[0], "second")
        self.assertEqual(agent.refine_summary_outer_round, 2)
        self.assertEqual(agent.review_calls, 1)
        self.assertEqual(len(agent.llm_timing_records), 3)
        self.assertEqual(
            agent.confidence_outer_retry_meta["stop_reason"],
            "max_total_llm_calls",
        )

    async def test_legacy_mode_returns_first_finish_regardless_of_confidence(self):
        agent = ScriptedRefineSummaryAgent(
            [("first", "", "20%"), ("second", "", "99%")],
            enabled=False,
        )

        result = await agent._run_refine_summary({"idx": 1, "problem": "question"})

        self.assertEqual(result[0], "first")
        self.assertEqual(agent.refine_summary_outer_round, 1)
        self.assertEqual(agent.review_calls, 0)

    async def test_retry_modes_and_highest_confidence_fallback(self):
        agent = ScriptedRefineSummaryAgent(
            [("first", "", "70%"), None, ("third", "", "90")],
            reviews=[review(0), review(1, keep="retain this source")],
        )

        result = await agent._run_refine_summary({"idx": 2, "problem": "question"})

        self.assertEqual(result[0], "third")
        self.assertEqual(agent.transitions, ["restart", "refine"])
        self.assertEqual(agent.review_calls, 2)
        self.assertEqual(agent.review_confidences, [70.0, None])
        self.assertEqual(agent.confidence_outer_retry_meta["selected_outer_round"], 3)
        self.assertEqual(agent.confidence_outer_retry_meta["selected_confidence"], 90.0)
        self.assertFalse(agent.confidence_outer_retry_meta["threshold_reached"])
        self.assertEqual(agent.messages[-1]["content"], "outer-3")

    async def test_first_finish_at_threshold_stops_without_another_review(self):
        agent = ScriptedRefineSummaryAgent(
            [("missing-confidence", "", ""), ("accepted", "", "95%"), ("unused", "", "99%")],
            reviews=[review(1, keep="useful clue")],
        )
        agent.enable_confidence_tiered_review = True

        result = await agent._run_refine_summary({"idx": 3, "problem": "question"})

        self.assertEqual(result[0], "accepted")
        self.assertEqual(agent.refine_summary_outer_round, 2)
        self.assertEqual(agent.review_calls, 1)
        self.assertTrue(agent.confidence_outer_retry_meta["threshold_reached"])

    async def test_resume_reviews_prior_outer_and_runs_only_outer_two(self):
        agent = ScriptedRefineSummaryAgent(
            [None, ("outer-two", "", "96%")],
            reviews=[review(0, problems="bad direction", focus="restart clean")],
        )
        prior = {
            "predicted": "outer-one",
            "evidence": "",
            "confidence": "70%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "assistant",
                    "content": "<tool_call><function=finish></function></tool_call>",
                },
            ],
        }

        result = await agent.run_confidence_outer_resume(
            {"idx": 5, "problem": "question"},
            prior,
            prior_result_path="prior/temp.json",
        )

        self.assertEqual(result[0], "outer-two")
        self.assertEqual(agent.review_calls, 1)
        self.assertEqual(agent.transitions, ["restart"])
        self.assertEqual(len(agent.confidence_outer_retry_meta["attempts"]), 2)
        self.assertEqual(agent.confidence_outer_retry_meta["selected_outer_round"], 2)
        self.assertTrue(agent.confidence_outer_retry_meta["threshold_reached"])

    async def test_resume_refine_falls_back_to_better_prior_finish(self):
        agent = ScriptedRefineSummaryAgent(
            [None, None],
            reviews=[review(1, keep="verified source", problems="missing link", focus="verify")],
        )
        prior = {
            "predicted": "outer-one",
            "evidence": "source",
            "confidence": "80%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "assistant",
                    "content": "<tool_call><function=finish></function></tool_call>",
                },
            ],
        }

        result = await agent.run_confidence_outer_resume(
            {"idx": 6, "problem": "question"},
            prior,
        )

        self.assertEqual(result[0], "outer-one")
        self.assertEqual(agent.transitions, ["refine"])
        self.assertEqual(agent.confidence_outer_retry_meta["selected_outer_round"], 1)
        self.assertFalse(agent.confidence_outer_retry_meta["threshold_reached"])

    async def test_resume_continues_through_configured_outer_rounds(self):
        agent = ScriptedRefineSummaryAgent(
            [
                None,
                ("outer-two", "", "80%"),
                None,
                ("outer-four", "", "96%"),
                ("unused", "", "99%"),
            ],
            reviews=[review(0), review(1, keep="useful clue"), review(0)],
        )
        prior = {
            "predicted": "outer-one",
            "evidence": "",
            "confidence": "70%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "assistant",
                    "content": "<tool_call><function=finish></function></tool_call>",
                },
            ],
        }

        result = await agent.run_confidence_outer_resume(
            {"idx": 7, "problem": "question"},
            prior,
        )

        self.assertEqual(result[0], "outer-four")
        self.assertEqual(agent.review_calls, 3)
        self.assertEqual(agent.transitions, ["restart", "refine", "restart"])
        self.assertEqual(len(agent.confidence_outer_retry_meta["attempts"]), 4)
        self.assertEqual(agent.confidence_outer_retry_meta["selected_outer_round"], 4)
        self.assertTrue(agent.confidence_outer_retry_meta["threshold_reached"])

    async def test_resume_reuses_prior_outer_one_at_threshold_without_review(self):
        agent = ScriptedRefineSummaryAgent([None] * 5, reviews=[])
        prior = {
            "predicted": "accepted outer one",
            "evidence": "source",
            "confidence": "95%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "assistant",
                    "content": "<tool_call><function=finish></function></tool_call>",
                },
            ],
        }
        prior_origin = {
            "origin_traj": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_start",
                    "outer_round": 1,
                    "content": "outer one",
                },
            ],
            "timing_stats": {
                "llm_calls": [
                    {
                        "round": 1,
                        "outer_round": 1,
                        "usage_delta": {"input_tokens": 10, "output_tokens": 5},
                    }
                ],
                "tool_calls": [],
                "update_context_calls": [],
                "rounds": [
                    {
                        "round": 1,
                        "outer_round": 1,
                        "turn_elapsed_seconds": 1.25,
                        "current_tokens_after_round": 20,
                    }
                ],
            },
        }

        result = await agent.run_confidence_outer_resume(
            {"idx": 8, "problem": "question"},
            prior,
            prior_origin=prior_origin,
        )

        self.assertEqual(result[0], "accepted outer one")
        self.assertEqual(agent.review_calls, 0)
        self.assertEqual(agent.confidence_outer_retry_meta["selected_outer_round"], 1)
        self.assertTrue(agent.confidence_outer_retry_meta["threshold_reached"])
        self.assertEqual(
            agent.confidence_outer_retry_meta["reused_outer_one_metrics"]["input_tokens"],
            10,
        )
        self.assertEqual(
            agent.confidence_outer_retry_meta["reused_outer_one_metrics"]["elapsed_seconds"],
            1.25,
        )

    def test_resume_reconstructs_outer_one_when_normal_saved_a_later_outer(self):
        initial_user = "original question\n"
        updated_context = "verified fact"
        prior = {
            "predicted": "later normal answer",
            "evidence": "later evidence",
            "confidence": "99%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "later normal outer"},
            ],
        }
        prior_origin = {
            "origin_traj": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": initial_user},
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_start",
                    "outer_round": 1,
                },
                {"role": "assistant", "content": "discarded before update"},
                {"role": "user", "content": "discarded observation"},
                {
                    "role": "event",
                    "event_type": "refine_summary_update",
                    "outer_round": 1,
                },
                {"role": "update", "content": updated_context},
                {"role": "assistant", "content": "outer one ended without finish"},
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_reset",
                    "finished_outer_round": 1,
                    "next_outer_round": 2,
                },
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_start",
                    "outer_round": 2,
                },
                {"role": "assistant", "content": "later normal finish"},
            ]
        }

        source = MainAgent._prepare_confidence_outer_resume_source(prior, prior_origin)

        self.assertTrue(source["outer_one_reconstructed"])
        self.assertEqual(source["source_final_outer_round"], 2)
        self.assertEqual(source["predicted"], "")
        self.assertEqual(source["confidence"], "")
        self.assertEqual([message["role"] for message in source["trajectory"]], ["system", "user", "assistant"])
        self.assertIn(updated_context, source["trajectory"][1]["content"])
        self.assertEqual(source["trajectory"][-1]["content"], "outer one ended without finish")
        self.assertFalse(
            any(
                item.get("event_type") == "refine_summary_outer_reset"
                for item in source["origin_traj"]
            )
        )

    def test_resume_recovers_finished_outer_one_when_normal_saved_a_later_outer(self):
        prior = {
            "predicted": "later answer",
            "evidence": "later evidence",
            "confidence": "96%",
            "trajectory": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "later outer"},
            ],
        }
        prior_origin = {
            "origin_traj": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "question"},
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_start",
                    "outer_round": 1,
                },
                {
                    "role": "assistant",
                    "content": (
                        "<tool_call><function=finish>"
                        "<parameter=answer>outer-one answer</parameter>"
                        "<parameter=evidences>outer-one evidence</parameter>"
                        "<parameter=confidence>82%</parameter>"
                        "</function></tool_call>"
                    ),
                },
                {
                    "role": "event",
                    "event_type": "confidence_outer_trajectory_review",
                    "outer_round": 1,
                },
                {
                    "role": "event",
                    "event_type": "refine_summary_outer_start",
                    "outer_round": 2,
                },
                {"role": "assistant", "content": "later normal finish"},
            ]
        }

        source = MainAgent._prepare_confidence_outer_resume_source(prior, prior_origin)

        self.assertTrue(source["outer_one_reconstructed"])
        self.assertEqual(source["source_final_outer_round"], 2)
        self.assertEqual(source["predicted"], "outer-one answer")
        self.assertEqual(source["evidence"], "outer-one evidence")
        self.assertEqual(source["confidence"], "82%")
        self.assertTrue(MainAgent._trajectory_has_finish_call(source["trajectory"]))

    def test_saved_finish_recovery_supports_native_tool_calls(self):
        messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": "finish",
                            "arguments": json.dumps(
                                {
                                    "answer": "native answer",
                                    "evidences": [{"url": "https://example.com"}],
                                    "confidence": "90%",
                                }
                            ),
                        },
                    }
                ],
            }
        ]

        result = MainAgent._finish_result_from_saved_messages(messages)

        self.assertEqual(result[0], "native answer")
        self.assertEqual(result[1], [{"url": "https://example.com"}])
        self.assertEqual(result[2], "90%")

    def test_resume_deadline_counts_only_reused_outer_one_time(self):
        prior_origin = {
            "timing_stats": {
                "rounds": [
                    {"outer_round": 1, "turn_elapsed_seconds": 1.25},
                    {"outer_round": 1, "turn_elapsed_seconds": 2.5},
                    {"outer_round": 2, "turn_elapsed_seconds": 100.0},
                ]
            }
        }

        self.assertEqual(confidence_outer_one_elapsed_seconds(prior_origin), 3.75)

    def test_reviewer_schema_requires_exact_four_ordered_keys(self):
        valid = (
            '{"trajectory_has_future_value":1,"information_to_keep":"fact",'
            '"problems_to_focus":"gap","next_round_focus":"source"}'
        )
        wrong_order = (
            '{"information_to_keep":"fact","trajectory_has_future_value":1,'
            '"problems_to_focus":"gap","next_round_focus":"source"}'
        )

        self.assertEqual(MainAgent._parse_trajectory_review(valid)["trajectory_has_future_value"], 1)
        self.assertIsNone(MainAgent._parse_trajectory_review(wrong_order))
        self.assertEqual(MainAgent._parse_confidence_percentage("95%"), 95.0)
        self.assertIsNone(MainAgent._parse_confidence_percentage(""))

    def test_refine_transition_uses_update_context_handoff(self):
        agent = MainAgent(
            {
                "model": "test-model",
                "context_limit_strategy": "refine_summary",
                "enable_confidence_outer_retry": True,
            },
            env=None,
            client=None,
            tokenizer=CharacterTokenizer(),
        )
        agent.append_message({"role": "user", "content": "original question"})
        agent.save_initial_state()
        agent.refine_summary_outer_round = 1

        transition = agent._prepare_confidence_outer_next_round(
            review(1, keep="verified fact", problems="weak date", focus="primary source"),
            data_idx=4,
            next_outer_round=2,
        )

        self.assertEqual(transition, "refine")
        self.assertEqual(len(agent.messages), 2)
        handoff_prompt = agent.messages[-1]["content"]
        self.assertIn("original question", handoff_prompt)
        self.assertIn("verified fact", handoff_prompt)
        self.assertIn("weak date", handoff_prompt)
        self.assertIn("primary source", handoff_prompt)
        self.assertEqual(agent.origin_messages[-1]["transition"], "refine")

    async def test_reviewer_exposes_complete_diagnostic_result(self):
        agent = MainAgent(
            {
                "model": "test-model",
                "context_limit_strategy": "refine_summary",
                "enable_confidence_outer_retry": True,
            },
            env=None,
            client=None,
            tokenizer=CharacterTokenizer(),
        )
        agent.messages = [{"role": "user", "content": "saved trajectory"}]

        raw_response = (
            '{"trajectory_has_future_value":1,"information_to_keep":"fact",'
            '"problems_to_focus":"gap","next_round_focus":"verify"}'
        )
        captured = {}

        async def fake_call_server(*args, **kwargs):
            captured["messages"] = kwargs["messages"]
            captured["response_format"] = kwargs["response_format"]
            agent._last_reasoning_content = "private reviewer reasoning"
            return raw_response

        agent.call_server = fake_call_server
        decision = await agent._review_confidence_outer_trajectory(
            {"idx": 9, "problem": "question"}
        )

        self.assertEqual(decision["trajectory_has_future_value"], 1)
        self.assertEqual(agent.last_confidence_outer_review["raw_response"], raw_response)
        self.assertEqual(
            agent.last_confidence_outer_review["raw_reasoning"],
            "private reviewer reasoning",
        )
        self.assertEqual(agent.last_confidence_outer_review["review_error"], "")
        review_prompt = captured["messages"][-1]["content"]
        self.assertIn("<trajectory_data>", review_prompt)
        self.assertIn("</trajectory_data>", review_prompt)
        self.assertGreater(
            review_prompt.index("Review it now"),
            review_prompt.index("</trajectory_data>"),
        )
        schema = captured["response_format"]["json_schema"]["schema"]
        self.assertEqual(schema["additionalProperties"], False)
        self.assertEqual(
            schema["required"],
            [
                "trajectory_has_future_value",
                "information_to_keep",
                "problems_to_focus",
                "next_round_focus",
            ],
        )
        payload = agent._build_payload(
            captured["messages"],
            response_format=captured["response_format"],
        )
        self.assertEqual(payload["response_format"], captured["response_format"])

    async def test_tiered_reviewer_routes_by_parsed_confidence(self):
        agent = MainAgent(
            {
                "model": "test-model",
                "context_limit_strategy": "refine_summary",
                "enable_confidence_outer_retry": True,
                "enable_confidence_tiered_review": True,
                "confidence_tiered_review_middle_threshold": 90,
            },
            env=None,
            client=None,
            tokenizer=CharacterTokenizer(),
        )
        agent.messages = [{"role": "user", "content": "saved trajectory"}]
        raw_response = (
            '{"trajectory_has_future_value":1,"information_to_keep":'
            '"[VERIFIED FINDINGS] fact\\n[FINAL CANDIDATE] Candidate A: RETAIN\\n'
            '[EXCLUDED CANDIDATES] NONE\\n[SUSPENDED CANDIDATES] NONE\\n'
            '[REUSABLE LEADS] source",'
            '"problems_to_focus":"gap","next_round_focus":'
            '"VERIFY_CURRENT: verify the decisive constraint"}'
        )
        captured = []

        async def fake_call_server(*args, **kwargs):
            captured.append(copy.deepcopy(kwargs["messages"]))
            return raw_response

        agent.call_server = fake_call_server

        decision = await agent._review_confidence_outer_trajectory(
            {"idx": 10, "problem": "question"},
            confidence_value=94.0,
        )
        self.assertEqual(decision["trajectory_has_future_value"], 1)
        self.assertEqual(agent.last_confidence_outer_review["review_error"], "")
        self.assertEqual(
            agent.last_confidence_outer_review["review_policy"],
            "middle_confidence",
        )
        self.assertIn("plausible but not established", captured[-1][0]["content"])
        self.assertIn("94%", captured[-1][1]["content"])

        await agent._review_confidence_outer_trajectory(
            {"idx": 10, "problem": "question"},
            confidence_value=90.0,
        )
        self.assertEqual(
            agent.last_confidence_outer_review["review_policy"],
            "middle_confidence",
        )

        await agent._review_confidence_outer_trajectory(
            {"idx": 10, "problem": "question"},
            confidence_value=89.0,
        )
        self.assertEqual(
            agent.last_confidence_outer_review["review_policy"],
            "low_or_missing_confidence",
        )
        self.assertIn("SUSPEND by default", captured[-1][0]["content"])
        self.assertIn("89%", captured[-1][1]["content"])

        await agent._review_confidence_outer_trajectory(
            {"idx": 10, "problem": "question"},
            confidence_value=None,
        )
        self.assertEqual(
            agent.last_confidence_outer_review["review_policy"],
            "low_or_missing_confidence",
        )
        self.assertIn("invalid_or_missing", captured[-1][1]["content"])

    def test_tiered_reviewer_validation_rejects_unstructured_refine_handoff(self):
        invalid = review(
            1,
            keep="Candidate A may be right",
            problems="missing evidence",
            focus="verify it",
        )

        decision, error = MainAgent._validate_tiered_trajectory_review(invalid)

        self.assertIsNone(decision)
        self.assertIn("missing labels", error)

    def test_tiered_reviewer_validation_clears_restart_handoff(self):
        decision, error = MainAgent._validate_tiered_trajectory_review(
            review(0, keep="must not survive", problems="bad path", focus="restart")
        )

        self.assertEqual(error, "")
        self.assertEqual(decision, review(0))

    def test_tiered_refine_transition_uses_candidate_aware_handoff(self):
        agent = MainAgent(
            {
                "model": "test-model",
                "context_limit_strategy": "refine_summary",
                "enable_confidence_outer_retry": True,
                "enable_confidence_tiered_review": True,
            },
            env=None,
            client=None,
            tokenizer=CharacterTokenizer(),
        )
        agent.append_message({"role": "user", "content": "original question"})
        agent.save_initial_state()
        agent.refine_summary_outer_round = 1

        transition = agent._prepare_confidence_outer_next_round(
            review(
                1,
                keep=(
                    "[VERIFIED FINDINGS] date clue verified\n"
                    "[FINAL CANDIDATE] Candidate A: SUSPEND\n"
                    "[EXCLUDED CANDIDATES] Candidate B: failed date constraint\n"
                    "[SUSPENDED CANDIDATES] Candidate A: missing identity evidence\n"
                    "[REUSABLE LEADS] archive index"
                ),
                problems="missing identity evidence",
                focus="SEARCH_ALTERNATIVE: derive candidates from the date clue",
            ),
            data_idx=11,
            next_outer_round=2,
        )

        self.assertEqual(transition, "refine")
        handoff_prompt = agent.messages[-1]["content"]
        self.assertIn("original question", handoff_prompt)
        self.assertIn("Candidate A: SUSPEND", handoff_prompt)
        self.assertIn("Do not use a suspended candidate as the default answer", handoff_prompt)

    def test_tiered_middle_threshold_must_be_below_acceptance_threshold(self):
        with self.assertRaises(ValueError):
            MainAgent(
                {
                    "model": "test-model",
                    "enable_confidence_outer_retry": True,
                    "confidence_outer_retry_threshold": 95,
                    "enable_confidence_tiered_review": True,
                    "confidence_tiered_review_middle_threshold": 95,
                },
                env=None,
                client=None,
                tokenizer=CharacterTokenizer(),
            )


if __name__ == "__main__":
    unittest.main()
