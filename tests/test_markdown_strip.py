"""Check: markdown syntax LLM output commonly carries is stripped before it'd hit TTS.
Run: python -m tests.test_markdown_strip
"""

from server.gateway.session import _strip_markdown

CASES = [
    ("# Heading\nBody text.", "Heading Body text."),
    ("Some **bold** and _italic_ text.", "Some bold and italic text."),
    ("- first\n- second", "first second"),
    ("Check the `code` here.", "Check the code here."),
    ("See [the docs](https://example.com) for more.", "See the docs for more."),
    ("Plain sentence, nothing to strip.", "Plain sentence, nothing to strip."),
    ("Line one\n\nLine two\nLine three", "Line one Line two Line three"),
]


def main() -> None:
    for raw, expected in CASES:
        got = _strip_markdown(raw)
        assert got == expected, f"{raw!r} -> {got!r}, expected {expected!r}"
    print(f"markdown strip PASS ({len(CASES)} cases)")


if __name__ == "__main__":
    main()
