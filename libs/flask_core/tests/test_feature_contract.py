"""
Feature contract tests
========================

Covers :mod:`flask_core.feature_contract` -- the Feature-side counterpart to
``test_app_framework.py``'s manifest coverage. Every reject reason gets its
own test (accept + reject paired per check), so a validation that silently
stopped firing fails here rather than only in production.

Fail-on-purpose proof: each reject test in ``TestParseFeatureContractReject``
was verified to actually catch its regression by temporarily commenting out
the corresponding check in ``feature_contract.py`` and confirming that test
(and only that test) goes red, then reverting. See the PR description for
the exact commands run.
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from flask_core.feature_contract import (
    REASON_BAD_FLAG,
    REASON_BAD_TIER,
    REASON_BAD_VERSION,
    REASON_MISSING_FIELD,
    REASON_MODULE_MISMATCH,
    REASON_NOT_NAMESPACED,
    REASON_UNKNOWN_MODULE,
    FeatureContract,
    FeatureContractError,
    parse_feature_contract,
)

VALID_CONTRACT: Dict[str, Any] = {
    "id": "bot.shoutout",
    "version": 1,
    "module": "bot",
    "requires_scopes": {"bot.command:write"},
    "min_tier": "free",
    "flag": "waddles.bot.shoutout",
}


def contract(**overrides: Any) -> Dict[str, Any]:
    """A fresh copy of VALID_CONTRACT with the given field overrides."""
    data = dict(VALID_CONTRACT)
    data.update(overrides)
    return data


class TestParseFeatureContractAccept:
    def test_valid_contract_parses_to_feature_contract(self) -> None:
        result = parse_feature_contract(contract())
        assert isinstance(result, FeatureContract)
        assert result.id == "bot.shoutout"
        assert result.version == 1
        assert result.module == "bot"
        assert result.requires_scopes == frozenset({"bot.command:write"})
        assert result.min_tier == "free"
        assert result.flag == "waddles.bot.shoutout"

    def test_higher_version_and_multiple_scopes_accepted(self) -> None:
        result = parse_feature_contract(
            contract(
                id="social.polls",
                module="social",
                version=3,
                min_tier="enterprise",
                requires_scopes={"social.poll:write", "social.poll:read"},
                flag="waddles.social.polls",
            )
        )
        assert result.version == 3
        assert result.min_tier == "enterprise"
        assert result.requires_scopes == frozenset({"social.poll:write", "social.poll:read"})

    def test_empty_requires_scopes_accepted(self) -> None:
        result = parse_feature_contract(contract(requires_scopes=()))
        assert result.requires_scopes == frozenset()

    def test_contract_is_frozen_and_slotted(self) -> None:
        result = parse_feature_contract(contract())
        with pytest.raises(AttributeError):
            result.id = "bot.other"  # type: ignore[misc]
        with pytest.raises(AttributeError):
            result.new_attr = "x"  # type: ignore[attr-defined]


class TestParseFeatureContractReject:
    """Each case exercises exactly one REASON_* code from feature_contract.py."""

    @pytest.mark.parametrize("missing_key", list(VALID_CONTRACT))
    def test_missing_required_field_rejected(self, missing_key: str) -> None:
        data = contract()
        del data[missing_key]
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(data)
        assert excinfo.value.reason == REASON_MISSING_FIELD

    def test_empty_string_id_rejected_as_missing(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(id=""))
        assert excinfo.value.reason == REASON_MISSING_FIELD

    def test_non_string_id_rejected(self) -> None:
        """A truthy non-string id (e.g. a list) passes `_require` but must
        still be rejected before it ever reaches the namespacing regex."""
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(id=["bot", "shoutout"]))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_non_namespaced_id_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(id="shoutout"))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_over_namespaced_id_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(id="bot.shoutout.extra"))
        assert excinfo.value.reason == REASON_NOT_NAMESPACED

    def test_unknown_module_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(
                contract(id="widgets.thing", module="widgets", flag="waddles.widgets.thing")
            )
        assert excinfo.value.reason == REASON_UNKNOWN_MODULE

    def test_module_mismatch_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(module="social"))
        assert excinfo.value.reason == REASON_MODULE_MISMATCH

    def test_version_zero_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(version=0))
        assert excinfo.value.reason == REASON_BAD_VERSION

    def test_negative_version_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(version=-1))
        assert excinfo.value.reason == REASON_BAD_VERSION

    def test_non_int_version_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(version="1"))
        assert excinfo.value.reason == REASON_BAD_VERSION

    def test_bool_version_rejected(self) -> None:
        """bool is an int subclass in Python -- must not sneak past the version check."""
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(version=True))
        assert excinfo.value.reason == REASON_BAD_VERSION

    def test_bad_tier_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(min_tier="gold"))
        assert excinfo.value.reason == REASON_BAD_TIER

    def test_flag_missing_waddles_prefix_rejected(self) -> None:
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(flag="bot.shoutout"))
        assert excinfo.value.reason == REASON_BAD_FLAG

    def test_flag_id_drift_rejected(self) -> None:
        """The load-bearing invariant: flag must equal 'waddles.' + id, not some other id."""
        with pytest.raises(FeatureContractError) as excinfo:
            parse_feature_contract(contract(flag="waddles.bot.raid"))
        assert excinfo.value.reason == REASON_BAD_FLAG
