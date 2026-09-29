import importlib.util
from pathlib import Path


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "BrowseComp" / "prompt.py"
_SPEC = importlib.util.spec_from_file_location("browsecomp_en_prompt", _PROMPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot import prompt module: {_PROMPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_LANGUAGE_RULE = """<LANGUAGE_RULE>
If the user asks in Chinese, answer in Chinese.
</LANGUAGE_RULE>"""

_ZH_RESEARCH_GUIDE = """<ZH_RESEARCH_GUIDE>
For Chinese multi-clue research questions, work compactly and converge:
- First identify the answer type, requested output field, and 3-5 hard clues that must be verified. Keep this analysis short.
- Keep a small candidate table with at most three serious candidates. For each candidate, check which hard clues match or fail.
- Search with distinctive clue combinations copied from the question. Prefer one precise query over many broad guesses.
- If two searches in the same direction add no useful evidence, stop that direction. Change angle or choose among current candidates.
- For relationship chains, resolve the chain in the order stated by the question. Do not jump from a famous clue to the most famous associated entity.
- For place/address questions, verify geography, distance, place type, and administrative name before choosing.
- For games, anime, books, songs, and papers, verify original title/official English name, release year, creator/actor/author clues, and series/worldview clues.
- When a candidate matches the answer type and most hard clues, finish. Do not continue open-ended exploration just to remove every minor uncertainty.
- The final answer should be only the requested field: a name, title, date, number, place, organization, or short English term.
</ZH_RESEARCH_GUIDE>"""

_ZH_USER_GUIDE = """\

Before searching, briefly list the answer type and key clues. During research, keep only a few plausible candidates and verify them against the hard clues. If repeated searches stop producing new evidence, make the best-supported choice and finish with the exact requested field.

Keep your reasoning concise. Avoid long inventories of possibilities unless they directly guide the next search.
"""

PROMPT_BUNDLE = dict(_MODULE.PROMPT_BUNDLE)
PROMPT_BUNDLE["system_prompt"] = (
    PROMPT_BUNDLE["system_prompt"].rstrip()
    + "\n\n"
    + _LANGUAGE_RULE
    + "\n\n"
    + _ZH_RESEARCH_GUIDE
)
PROMPT_BUNDLE["user_prompt"] = (
    PROMPT_BUNDLE["user_prompt"].rstrip() + "\n\n" + _ZH_USER_GUIDE
)
