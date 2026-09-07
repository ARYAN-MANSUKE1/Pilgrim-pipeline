"""Self-check: the thinking knob must never be dropped.

Deleting thinkingConfig on a 400 (what the code used to do) does not mean "no
thinking" -- it reverts to the model's default budget, which billed 2,413 thought
tokens per call at the output rate. Run: python check_thinking_cfg.py
"""
import app.tasks.gemini_translate as g
from app.config import settings

def cfg_for(model):
    settings.gemini_model = model
    g._THINKING_SWAPPED = False
    return g._thinking_cfg()

# 3.x gets thinkingLevel; 2.x gets thinkingBudget
for m in ("gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"):
    assert cfg_for(m) == {"thinkingLevel": "minimal"}, (m, cfg_for(m))
for m in ("gemini-2.5-flash", "gemini-2.0-flash"):
    assert cfg_for(m) == {"thinkingBudget": 0}, (m, cfg_for(m))

# a 400 must SWAP the spelling, never yield an empty config
for m in ("gemini-3.1-flash-lite", "gemini-2.5-flash"):
    settings.gemini_model = m
    g._THINKING_SWAPPED = False
    first = g._thinking_cfg()
    g._THINKING_SWAPPED = True
    second = g._thinking_cfg()
    assert second and second != first, (m, first, second)
    assert set(second) <= {"thinkingLevel", "thinkingBudget"}, second

# every call site must pass _thinking_cfg(), not a literal
src = open("app/tasks/gemini_translate.py", encoding="utf-8").read()
body = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
assert '{"thinkingBudget": 0}' not in body.split("def _thinking_cfg")[1].split("\n\n\n")[1], \
    "a call site hardcodes thinkingBudget -- it will 400 on Gemini 3.x"
print("thinking-config self-check OK")
