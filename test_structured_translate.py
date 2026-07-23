"""
Proves translate_html() preserves structure: every <img>, every tag, and every
blank-line paragraph break survives untouched, while the text is translated.

Run:  python test_structured_translate.py
No API key needed — a mock translator stands in for Sarvam.
"""

import re

from app.tasks.structured_translate import translate_html

# A representative slice of real temple content: heading, a paragraph with a
# MID-sentence inline image, a blank-line paragraph break, and a <ul> list.
SAMPLE = (
    '<h1><strong>Agasi Mata Swapna Mandir</strong></h1>\n'
    '<h3><strong>Dhuliya Road, Bardoli, Dist. Surat</strong></h3>\n'
    '<img class="alignleft wp-image-11028 size-full" src="https://x/4-1-7.jpg" alt="" width="1000" height="750" />'
    'The Agasi Mata temple in Bardoli is over 400 years old. '
    'Devotees believe prayers here are fulfilled.<img class="alignright wp-image-11040 size-full" '
    'src="https://x/16-1-3.jpg" alt="" width="750" height="1000" /> It draws hundreds of pilgrims.\n'
    '\n'
    'The temple is open from 6:00 am to 12:00 pm and again from 3:00 pm to 9:00 pm.\n'
    '<h3><strong>Key Highlights</strong></h3>\n'
    '<ul>\n'
    ' \t<li>Located 4 km from Bardoli and 39 km from Surat.</li>\n'
    ' \t<li>Adequate parking facilities are available.</li>\n'
    '</ul>'
)


def mock_translate(text, src, tgt):
    """Fake translator: wraps words so we can prove text (and only text) changed.
    Deliberately strips outer whitespace like a real API would, to test edge-ws handling."""
    return f"<{tgt}>{text.strip()}</{tgt}>"


def imgs(s):
    return re.findall(r'<img[^>]*>', s)


def tags(s):
    return re.findall(r'</?(?:h1|h3|ul|li|strong)\b[^>]*>', s)


def main():
    out = translate_html(SAMPLE, "en", "mr", mock_translate)

    checks = []

    # 1) Every <img> tag preserved exactly and in order.
    checks.append(("images identical & in order", imgs(SAMPLE) == imgs(out)))

    # 2) Every structural tag preserved exactly and in order.
    checks.append(("structural tags identical & in order", tags(SAMPLE) == tags(out)))

    # 3) Blank-line paragraph breaks preserved (count of \n\n boundaries).
    sep = re.compile(r"(?:\r?\n[ \t]*){2,}")
    checks.append(("paragraph breaks preserved",
                   len(sep.findall(SAMPLE)) == len(sep.findall(out)) == 1))

    # 4) The text actually got translated (mock marker present).
    checks.append(("text was translated", "<mr>" in out))

    # 5) No tag leaked into the translator (mock never wrapped a tag).
    checks.append(("no tag was sent to translator", "<mr><img" not in out and "<mr><h" not in out))

    # 6) Round-trip with an identity translator returns the input byte-for-byte.
    identity = translate_html(SAMPLE, "en", "mr", lambda t, s, g: t)
    checks.append(("identity translator is a perfect round-trip", identity == SAMPLE))

    print("\n--- translated output ---\n")
    print(out)
    print("\n--- checks ---")
    ok = True
    for name, passed in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed

    print("\nRESULT:", "ALL PASS ✅" if ok else "FAILURES ❌")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
