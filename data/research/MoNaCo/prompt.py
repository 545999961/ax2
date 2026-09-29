from pathlib import Path
import importlib.util


_PROMPT_PATH = Path(__file__).resolve().parents[1] / "BrowseComp" / "prompt.py"
_SPEC = importlib.util.spec_from_file_location("browsecomp_prompt", _PROMPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot import BrowseComp prompt module: {_PROMPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

PROMPT_BUNDLE = _MODULE.PROMPT_BUNDLE
TOOLS = _MODULE.TOOLS
