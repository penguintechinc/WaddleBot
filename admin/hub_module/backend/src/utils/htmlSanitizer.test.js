/**
 * Tests for `htmlToText` -- the `js-xss`-based replacement for
 * `aiKnowledgeService.js`'s old regex `<script>`/`<style>` stripping
 * (CodeQL `js/incomplete-multi-character-sanitization` /
 * `js/bad-tag-filter`).
 *
 * Fail-first proof (executed, not narrated): reimplemented the original
 * three-step regex pipeline standalone
 * (`.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')`,
 * `.replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')`,
 * `.replace(/<[^>]+>/g, ' ')` -- the exact former inline body in
 * `fetchSitemapPages`) and ran it against this file's
 * `unterminatedFinalScriptTag` payload -- output was
 * `'foobar<script src=//evil.example/x.js'`, a live `<script`
 * substring, because the catch-all tag-stripper requires a *subsequent*
 * `>` in the string to match and remove a tag, and this payload has
 * none after the final malicious open tag. `htmlToText` neutralizes the
 * same payload (see `does not survive the unterminated-final-tag
 * bypass`).
 *
 * Run with the repo's configured runner: `npm test` (node --test).
 */
import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

import { htmlToText } from './htmlSanitizer.js';

describe('htmlToText — nested/malformed tag bypasses', () => {
  it('neutralizes a nested <scr<script> payload', () => {
    const result = htmlToText('<scr<script>ipt>alert(1)</scr</script>ipt>');
    assert.equal(/<script/i.test(result), false);
    assert.equal(/<\/script/i.test(result), false);
  });

  it('strips an svg/onload payload with no surviving tag', () => {
    const result = htmlToText('before<svg/onload=alert(1)>after');
    assert.equal(/<svg/i.test(result), false);
    assert.equal(/onload/i.test(result), false);
  });

  it('strips an img/onerror payload with no surviving tag', () => {
    const result = htmlToText('<img src=x onerror="alert(document.cookie)">');
    assert.equal(/<img/i.test(result), false);
    assert.equal(/onerror/i.test(result), false);
  });
});

describe('htmlToText — unterminated final tag (the confirmed regex-pipeline bypass)', () => {
  it('does not survive the unterminated-final-tag bypass', () => {
    // No '>' anywhere after the final malicious opening tag -- the old
    // catch-all `/<[^>]+>/g` cannot find a closer for it and the
    // literal '<script' substring survived untouched (confirmed above).
    const payload = 'foo<script>bad</script>bar<script src=//evil.example/x.js';
    const result = htmlToText(payload);
    assert.equal(/<script/i.test(result), false);
    assert.equal(result.includes('bad'), false);
  });

  it('strips case- and attribute-varied script tags', () => {
    const payload = '<SCRIPT SRC="//evil.example/x.js" defer>steal()</SCRIPT>tail';
    const result = htmlToText(payload);
    assert.equal(/<script/i.test(result), false);
    assert.equal(result.includes('steal()'), false);
    assert.equal(result.trim(), 'tail');
  });
});

describe('htmlToText — style and plain content', () => {
  it('drops <style> element content', () => {
    const result = htmlToText('<style>body{background:url(javascript:alert(1))}</style>visible');
    assert.equal(/<style/i.test(result), false);
    assert.equal(result.includes('javascript:alert'), false);
    assert.equal(result.trim(), 'visible');
  });

  it('strips ordinary tags but keeps their text', () => {
    assert.equal(htmlToText("<div class='x'>Hello <b>World</b></div>"), 'Hello World');
  });

  it('passes plain text through unchanged', () => {
    assert.equal(htmlToText('plain text here'), 'plain text here');
  });
});

describe('htmlToText — blanket sweep', () => {
  const payloads = [
    '<script>alert(1)</script>',
    '<ScRiPt>alert(1)</sCrIpT>',
    "<script type='text/javascript'>alert(1)</script>",
    '<style>*{}</style><script>alert(1)</script>',
    '<scr<script>ipt>alert(1)</script>',
  ];

  for (const payload of payloads) {
    it(`never leaves a live <script tag for: ${payload}`, () => {
      const result = htmlToText(payload);
      assert.equal(/<script/i.test(result), false);
      assert.equal(/<\/script/i.test(result), false);
    });
  }
});
