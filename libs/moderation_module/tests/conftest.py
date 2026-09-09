"""Shared fixtures/helpers for moderation_module's own tests."""

from __future__ import annotations


def ollama_logprobs_response(*, yes_logprob: float | None, no_logprob: float | None) -> dict:
    """Build a canned Ollama `/api/generate` JSON body carrying `Yes`/`No` `top_logprobs`.

    Shape captured from a real call against Ollama 0.33.3 + `shieldgemma:2b`
    (see `tests/test_local_ollama_live.py`) -- `top_logprobs` entries other
    than `Yes`/`No` are omitted here since `_extract_yes_no_logprobs` only
    ever reads those two.
    """
    top_logprobs = []
    if yes_logprob is not None:
        top_logprobs.append({"token": "Yes", "logprob": yes_logprob})
    if no_logprob is not None:
        top_logprobs.append({"token": "No", "logprob": no_logprob})
    first_token = {
        "token": "Yes",
        "logprob": yes_logprob if yes_logprob is not None else -20.0,
        "top_logprobs": top_logprobs,
    }
    return {
        "model": "shieldgemma:2b",
        "response": "Yes" if (yes_logprob or -99) > (no_logprob or -99) else "No",
        "done": True,
        "logprobs": [first_token],
    }
