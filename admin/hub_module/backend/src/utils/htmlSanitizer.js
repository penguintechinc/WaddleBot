/**
 * Real HTML-parser text extraction for the AI-knowledge crawler --
 * JS twin of `hub_api/services/bot_ai_knowledge.py`'s `_html_to_text`.
 *
 * Replaces `aiKnowledgeService.js`'s former three-step regex pipeline
 * (strip `<script>`, strip `<style>`, strip every remaining `<...>`)
 * that CodeQL flagged as bypassable
 * (`js/incomplete-multi-character-sanitization` / `js/bad-tag-filter`):
 * a crafted payload such as
 * `foo<script>bad</script>bar<script src=//evil.example/x.js` (no `>`
 * anywhere after the final malicious open tag) leaves a live,
 * unterminated `<script` substring in the old pipeline's output, because
 * its catch-all `/<[^>]+>/g` tag-stripper requires a *subsequent* `>` in
 * the string to match and remove a tag.
 */
import xss from 'xss';

/**
 * Strip all markup from `html`, returning plain text. Uses `js-xss`'s
 * allowlist-based tokenizer (real tag-boundary tracking, not a regex
 * over raw string positions) with an empty allowlist -- every tag is
 * removed, and `<script>`/`<style>` element *content* is dropped too
 * (not just the tags), matching the original pipeline's intent of never
 * indexing raw JS/CSS source as page text.
 * @param {string} html
 * @returns {string}
 */
export function htmlToText(html) {
  return xss(html, {
    whiteList: {},
    stripIgnoreTag: true,
    stripIgnoreTagBody: ['script', 'style'],
  });
}
