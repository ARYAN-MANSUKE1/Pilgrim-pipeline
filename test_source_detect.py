"""
Proves source-language detection: pick the populated field by visible text,
ignore placeholders and image-only fields, and flag ambiguity.

Run:  python test_source_detect.py
"""

from app.tasks.source_detect import (
    detect_source_language,
    pick_source,
    visible_text_length,
)

BODY_MR = "<h1><strong>अगस्ती ऋषी आश्रम</strong></h1>\n" + ("एका घोटात संपूर्ण समुद्राचे पाणी. " * 40)
BODY_EN = "<h3>Agasi Mata</h3>\n" + ("The temple in Bardoli is very old. " * 40)
IMG_ONLY = '<img class="alignleft" src="https://x/a.jpg" width="1000" height="750" />'
PLACEHOLDER = "<p>Coming soon</p>"

results = []


def check(name, cond):
    results.append((name, cond))


# 1) Fresh temple: only Marathi populated -> source is mr, not ambiguous.
r = detect_source_language({"mr": BODY_MR, "en": "", "hi": None})
check("marathi-only -> source mr", r.source == "mr" and not r.ambiguous)

# 2) English-source temple.
r = detect_source_language({"mr": PLACEHOLDER, "en": BODY_EN, "hi": ""})
check("english-source -> source en", r.source == "en" and not r.ambiguous)

# 3) Image-only / placeholder fields do NOT count as a source.
check("image-only has ~no visible text", visible_text_length(IMG_ONLY) < 50)
r = detect_source_language({"mr": IMG_ONLY, "en": PLACEHOLDER, "hi": ""})
check("no real content -> source None", r.source is None)

# 4) Two populated candidates -> flagged ambiguous; default priority picks mr.
r = detect_source_language({"mr": BODY_MR, "en": BODY_EN, "hi": ""})
check("two candidates -> ambiguous", r.ambiguous and set(r.qualified) == {"mr", "en"})
check("default priority mr>en>hi picks mr", r.source == "mr")

# 5) Priority breaks ties deterministically when ambiguous.
r = detect_source_language({"mr": BODY_MR, "en": BODY_EN, "hi": ""}, priority=("en", "mr", "hi"))
check("priority picks en over mr", r.source == "en")


# 6) A temple written only in another language (added via "Other"): that language is the source.
BODY_TA = "<p>" + ("இந்தக் கோயில் ஒரு ஆற்றின் கரையில் அமைந்துள்ளது. " * 12) + "</p>"
check("tamil-only temple -> source ta", pick_source({"mr": "", "en": "", "hi": None, "ta": BODY_TA, "gj": PLACEHOLDER}) == "ta")
check("...but Marathi/English/Hindi still win when present", pick_source({"mr": "", "en": BODY_EN, "hi": "", "ta": BODY_TA}) == "en")
check("nothing anywhere -> no source", pick_source({"mr": "", "en": PLACEHOLDER, "ta": IMG_ONLY}) is None)

print("--- checks ---")
ok = True
for name, passed in results:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    ok = ok and passed
print("\nRESULT:", "ALL PASS ✅" if ok else "FAILURES ❌")
raise SystemExit(0 if ok else 1)
