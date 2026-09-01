"""HTML text-extraction sanitization tests -- `services/bot_ai_knowledge.py`.

Covers the CodeQL `py/bad-tag-filter` finding on the module's old
regex-based `<script>`/`<style>` stripping (`_SCRIPT_RE`/`_STYLE_RE`/
`_TAG_RE`, replaced by `_html_to_text`'s `HTMLParser`-based extractor).

Fail-first proof (executed, not narrated): reimplemented the original
three-step regex pipeline standalone
(`SCRIPT_RE.sub("", frag); STYLE_RE.sub("", text); TAG_RE.sub(" ", text)`,
the exact former `_SCRIPT_RE`/`_STYLE_RE`/`_TAG_RE` bodies) and ran it
against `TestUnterminatedScriptBypass`'s payload
(`"foo<script>bad</script>bar<script src=//evil.example/x.js"`) --
output was `'foobar<script src=//evil.example/x.js'`, a live
`<script` substring, because the catch-all `_TAG_RE` requires a
*subsequent* `>` in the string to match and strip a tag, and this
payload has none after the final malicious open tag. `_html_to_text`
(the `HTMLParser`-based replacement) neutralizes the same payload:
`test_unterminated_final_script_tag_does_not_survive` passes.
"""

from __future__ import annotations

import pytest

from services.bot_ai_knowledge import _html_to_text


class TestNestedScriptBypass:
    """Nested-tag payloads that defeat a single-pass `<script>...</script>` regex."""

    def test_nested_script_tag_is_neutralized(self) -> None:
        # Nested/malformed tag payload: a naive regex can match tag
        # boundaries at the wrong string positions here and leave a
        # reconstructible `<script...>`/`</script>` pair in its output.
        # The security invariant under test is that no live tag
        # survives -- inert leftover text (e.g. "alert(1)" as plain
        # characters, no longer inside any tag) is not itself dangerous.
        payload = "<scr<script>ipt>alert(1)</scr</script>ipt>"
        result = _html_to_text(payload)
        assert "<script" not in result.lower()
        assert "</script" not in result.lower()

    def test_svg_onload_payload_has_no_surviving_tag(self) -> None:
        payload = "before<svg/onload=alert(1)>after"
        result = _html_to_text(payload)
        assert "<svg" not in result.lower()
        assert "onload" not in result.lower()
        assert result == "beforeafter"

    def test_img_onerror_payload_has_no_surviving_tag(self) -> None:
        payload = '<img src=x onerror="alert(document.cookie)">'
        result = _html_to_text(payload)
        assert "<img" not in result.lower()
        assert "onerror" not in result.lower()


class TestUnterminatedScriptBypass:
    """The exact bypass proven against the old regex pipeline (see module docstring).

    `foo<script>bad</script>bar<script src=//evil.example/x.js` (no `>`
    anywhere after the final malicious open tag): the old pipeline's
    catch-all `_TAG_RE = re.compile(r"<[^>]+>")` requires a *subsequent*
    `>` to match and strip a tag -- with none present, a live,
    unterminated `<script src=...` substring survived untouched in the
    regex pipeline's output (confirmed: `old_html_to_text(payload)` ==
    `'foobar<script src=//evil.example/x.js'`, `<script` present). A
    real parser has no such reliance on a closing delimiter appearing
    later in the string -- it tracks that a `<script` element is open
    from the tokenizer's own state, not from finding a matching `>`.
    """

    def test_unterminated_final_script_tag_does_not_survive(self) -> None:
        payload = "foo<script>bad</script>bar<script src=//evil.example/x.js"
        result = _html_to_text(payload)
        assert "<script" not in result.lower()
        assert "bad" not in result  # dropped as content of the first, closed <script>

    def test_case_and_attribute_variation_is_still_stripped(self) -> None:
        payload = '<SCRIPT SRC="//evil.example/x.js" defer>steal()</SCRIPT>tail'
        result = _html_to_text(payload)
        assert "<script" not in result.lower()
        assert "steal()" not in result
        assert result == "tail"


class TestStyleAndPlainContent:
    def test_style_element_content_is_dropped(self) -> None:
        payload = "<style>body{background:url(javascript:alert(1))}</style>visible"
        result = _html_to_text(payload)
        assert "<style" not in result.lower()
        assert "javascript:alert" not in result
        assert result == "visible"

    def test_ordinary_tags_are_stripped_but_text_kept(self) -> None:
        payload = "<div class='x'>Hello <b>World</b></div>"
        assert _html_to_text(payload) == "Hello World"

    def test_plain_text_passes_through_unchanged(self) -> None:
        assert _html_to_text("plain text here") == "plain text here"

    def test_html_entities_are_decoded(self) -> None:
        assert _html_to_text("A &amp; B &lt;tag&gt;") == "A & B <tag>"


@pytest.mark.parametrize(
    "payload",
    [
        "<script>alert(1)</script>",
        "<ScRiPt>alert(1)</sCrIpT>",
        "<script type='text/javascript'>alert(1)</script>",
        "<style>*{}</style><script>alert(1)</script>",
        "<scr<script>ipt>alert(1)</script>",
    ],
)
def test_no_payload_leaves_a_reconstructible_script_tag(payload: str) -> None:
    """Blanket sweep: none of these ever leave a `<script` substring in the output."""
    result = _html_to_text(payload)
    assert "<script" not in result.lower()
    assert "</script" not in result.lower()
