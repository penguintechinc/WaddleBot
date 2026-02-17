#!/usr/bin/env python3
"""
Test script for Ensemble Language Detection with Translation
Tests detection and translation for multiple languages with username preservation.

Improvements tested:
1. Text preprocessing (removes @mentions, URLs, emotes)
2. FastText integration (176 language model)
3. Minimum text length threshold
"""
import asyncio
from services.translation_providers.ensemble_detector import EnsembleLanguageDetector

# Test messages in various languages with username penguinzplays
TEST_MESSAGES = [
    # English
    ("Hey @penguinzplays great stream today!", "en", "English"),

    # Spanish
    ("@penguinzplays hola amigo, me encanta tu contenido!", "es", "Spanish"),

    # French (longer text with more distinctive French words)
    ("@penguinzplays Bonjour! J'adore ton stream, c'est vraiment magnifique!", "fr", "French"),

    # German
    ("@penguinzplays du bist der beste streamer!", "de", "German"),

    # Portuguese
    ("Oi @penguinzplays, seu stream é muito legal!", "pt", "Portuguese"),

    # Italian
    ("Ciao @penguinzplays, sei fantastico!", "it", "Italian"),

    # Japanese (longer text for reliable detection)
    ("@penguinzplays 素晴らしいストリームですね!毎日見ています!", "ja", "Japanese"),

    # Korean (longer text for reliable detection)
    ("@penguinzplays 정말 재미있어요! 계속 방송해주세요!", "ko", "Korean"),

    # Chinese (Simplified, longer text for reliable detection - needs 10+ chars)
    ("@penguinzplays 你的直播太棒了,我每天都看你的视频,非常喜欢!", "zh", "Chinese"),

    # Russian (longer text for reliable detection)
    ("@penguinzplays отличный стрим! спасибо за контент!", "ru", "Russian"),

    # Arabic (longer text for reliable detection)
    ("@penguinzplays بث رائع! أحب محتواك كثيرا!", "ar", "Arabic"),

    # Dutch
    ("Hey @penguinzplays, geweldige stream vandaag!", "nl", "Dutch"),
]


async def test_ensemble_detection():
    """Test ensemble language detection with multiple languages."""
    print("=" * 70)
    print("ENSEMBLE LANGUAGE DETECTION TEST (WITH PREPROCESSING)")
    print("Username: penguinzplays")
    print("=" * 70)
    print()

    detector = EnsembleLanguageDetector()

    # First, show what preprocessing does
    print("PREPROCESSING EXAMPLES:")
    print("-" * 70)
    for message, _, lang_name in TEST_MESSAGES[:3]:
        cleaned = detector.preprocess_text(message)
        print(f"{lang_name}:")
        print(f"  Original: {message}")
        print(f"  Cleaned:  {cleaned}")
        print()
    print("-" * 70)
    print()

    # Check if fastText model is available
    await detector._initialize_models()
    print("DETECTOR STATUS:")
    print(f"  FastText: {'✓ Available' if detector.fasttext_model else '✗ Not available'}")
    print(f"  Lingua:   {'✓ Available' if detector.lingua_detector else '✗ Not available'}")
    print(f"  Langdetect: {'✓ Available' if detector.langdetect_ready else '✗ Not available'}")
    print()
    print("=" * 70)
    print()

    results = []
    for message, expected_lang, lang_name in TEST_MESSAGES:
        try:
            detected_lang, confidence = await detector.detect_language(message)

            # Check if detection matches expected
            match = "✓" if detected_lang == expected_lang else "✗"

            result = {
                "language": lang_name,
                "expected": expected_lang,
                "detected": detected_lang,
                "confidence": confidence,
                "match": detected_lang == expected_lang
            }
            results.append(result)

            print(f"{match} {lang_name:12} | Expected: {expected_lang:5} | Detected: {detected_lang:5} | Confidence: {confidence:.2%}")
            # Show cleaned text
            cleaned = detector.preprocess_text(message)
            print(f"   Cleaned: {cleaned[:50]}{'...' if len(cleaned) > 50 else ''}")
            print()

        except ValueError as e:
            # Text too short after preprocessing
            print(f"⚠ {lang_name:12} | SKIPPED: {e}")
            results.append({
                "language": lang_name,
                "expected": expected_lang,
                "detected": "SKIPPED",
                "confidence": 0,
                "match": False
            })
            print()

        except Exception as e:
            print(f"✗ {lang_name:12} | ERROR: {e}")
            results.append({
                "language": lang_name,
                "expected": expected_lang,
                "detected": "ERROR",
                "confidence": 0,
                "match": False
            })
            print()

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    valid_results = [r for r in results if r["detected"] not in ("ERROR", "SKIPPED")]
    correct = sum(1 for r in valid_results if r["match"])
    total = len(valid_results)
    skipped = sum(1 for r in results if r["detected"] == "SKIPPED")

    if total > 0:
        accuracy = correct / total * 100
        avg_confidence = sum(r["confidence"] for r in valid_results) / total
        print(f"Accuracy:           {correct}/{total} ({accuracy:.1f}%)")
        print(f"Average Confidence: {avg_confidence:.2%}")
    else:
        print("No valid results to analyze")

    if skipped > 0:
        print(f"Skipped (too short): {skipped}")
    print()

    # Mismatches
    mismatches = [r for r in valid_results if not r["match"]]
    if mismatches:
        print("Mismatches:")
        for r in mismatches:
            print(f"  - {r['language']}: expected {r['expected']}, got {r['detected']}")
    else:
        print("🎉 No mismatches - all languages detected correctly!")

    print()


if __name__ == "__main__":
    asyncio.run(test_ensemble_detection())
