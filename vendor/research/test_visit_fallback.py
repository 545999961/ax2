import os
import asyncio
import unittest
from unittest import mock

import local_search
from hle_0724_vendor import visit_fallback


class VisitFallbackTest(unittest.TestCase):
    def test_classifies_reader_errors_hidden_in_success_responses(self):
        self.assertEqual(
            visit_fallback.classify_visit_content("Error: Connection error occurred"),
            "connection_error",
        )
        self.assertEqual(
            visit_fallback.classify_visit_content(
                '{"code":402,"name":"InsufficientBalanceError","status":40203}'
            ),
            "insufficient_balance",
        )
        self.assertEqual(
            visit_fallback.classify_visit_content(
                "Warning: Target URL returned error 403: Forbidden"
            ),
            "target_access_denied_403",
        )

    def test_connection_error_retries_with_cache_type_no(self):
        connection = visit_fallback.VisitFetchResult(
            ok=False,
            source="jina_new",
            error_type="connection_error",
        )
        success = visit_fallback.VisitFetchResult(
            ok=True,
            source="jina_no",
            content="useful page content",
        )
        with mock.patch.object(
            visit_fallback,
            "_jina_fetch",
            side_effect=[connection, success],
        ) as jina_fetch, mock.patch.object(
            visit_fallback,
            "direct_fetch",
        ) as direct_fetch:
            result = visit_fallback.fetch_url_with_fallback(
                "https://example.com/article",
                "token",
            )
        self.assertTrue(result.ok)
        self.assertEqual([call.args[2] for call in jina_fetch.call_args_list], ["new", "no"])
        direct_fetch.assert_not_called()

    def test_pdf_uses_local_parser_before_jina(self):
        pdf_success = visit_fallback.VisitFetchResult(
            ok=True,
            source="direct_pdf_pymupdf",
            content="PDF text",
        )
        with mock.patch.object(
            visit_fallback,
            "direct_fetch",
            return_value=pdf_success,
        ) as direct_fetch, mock.patch.object(
            visit_fallback,
            "_jina_fetch",
        ) as jina_fetch:
            result = visit_fallback.fetch_url_with_fallback(
                "https://example.com/paper.pdf",
                "token",
            )
        self.assertTrue(result.ok)
        direct_fetch.assert_called_once_with(
            "https://example.com/paper.pdf",
            expect_pdf=True,
        )
        jina_fetch.assert_not_called()

    def test_environment_default_is_enabled_and_can_be_disabled(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(visit_fallback.visit_fallback_default_enabled())
        with mock.patch.dict(os.environ, {"ENABLE_VISIT_FALLBACK": "0"}, clear=True):
            self.assertFalse(visit_fallback.visit_fallback_default_enabled())

    def test_pdf_text_quality_rejects_mojibake(self):
        self.assertTrue(
            visit_fallback._text_looks_readable(
                "This is readable extracted PDF text with enough ordinary words. " * 4
            )
        )
        self.assertFalse(visit_fallback._text_looks_readable("Îêðóæíîñòè " * 30))

    def test_browsecomp_switch_preserves_legacy_path(self):
        result = visit_fallback.VisitFetchResult(
            ok=True,
            content="enhanced page content " * 20,
            source="direct_http",
            attempts=["direct_http:ok"],
        )

        async def run_both():
            with mock.patch.object(
                local_search,
                "fetch_url_with_fallback",
                return_value=result,
            ) as enhanced, mock.patch.object(
                local_search,
                "open",
                new=mock.AsyncMock(return_value="legacy page content " * 20),
            ) as legacy, mock.patch.object(
                local_search,
                "_summarize_page_content",
                new=mock.AsyncMock(return_value="summary"),
            ):
                await local_search.readpage_jina(
                    "https://example.com/new",
                    "goal",
                    None,
                    None,
                    "model",
                    None,
                    enable_visit_fallback=True,
                )
                await local_search.readpage_jina(
                    "https://example.com/legacy",
                    "goal",
                    None,
                    None,
                    "model",
                    None,
                    enable_visit_fallback=False,
                )
                return enhanced.call_count, legacy.call_count

        enhanced_calls, legacy_calls = asyncio.run(run_both())
        self.assertEqual(enhanced_calls, 1)
        self.assertEqual(legacy_calls, 1)


if __name__ == "__main__":
    unittest.main()
