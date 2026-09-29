import importlib.util
from pathlib import Path


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "WideSearch-en" / "prompt.py"
_SPEC = importlib.util.spec_from_file_location("widesearch_en_prompt", _PROMPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot import prompt module: {_PROMPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

_LANGUAGE_RULE = """<LANGUAGE_RULE>
If the user asks in Chinese, answer in Chinese.
</LANGUAGE_RULE>"""

PROMPT_BUNDLE = dict(_MODULE.PROMPT_BUNDLE)
PROMPT_BUNDLE["system_prompt"] = (
    PROMPT_BUNDLE["system_prompt"].rstrip() + "\n\n" + _LANGUAGE_RULE
)
TOOLS = _MODULE.TOOLS
