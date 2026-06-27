"""
Unit tests for logiclayer.reporting.formatter.

This test suite validates:

    - Raw verdict parsing
    - Individual verdict formatting
    - Full report generation
    - Error handling
    - Summary statistics

Note:
    Hallucination detection tests removed per owner review.
    Claims with no evidence are now treated as unverified.

Run:

    pytest tests/test_formatter.py -v

Coverage Goals:
    - Happy paths
    - Invalid inputs
    - Formatting correctness
    - Section ordering
    - Parse error handling
"""

from __future__ import annotations

from typing import Any

import pytest

from logiclayer.reporting.formatter import (
    Verdict,
    _parse_verdict,
    format_report,
    format_verdict,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def verified_verdict() -> dict[str, Any]:
    """Sample verified verdict."""
    return {
        "claim": "Python was created by Guido van Rossum",
        "verdict": "verified",
        "evidence": "Python was created by Guido van Rossum",
        "source_url": (
            "https://www.python.org/doc/essays/foreword/"
        ),
        "correction": None,
        "tier_used": "local",
    }


@pytest.fixture
def wrong_verdict() -> dict[str, Any]:
    """Sample wrong verdict."""
    return {
        "claim": "Python was first released in 1989",
        "verdict": "wrong",
        "evidence": (
            "Python 0.9.0 was released in February 1991"
        ),
        "source_url": (
            "https://en.wikipedia.org/wiki/Python_"
        ),
        "correction": (
            "Python was first released in February 1991"
        ),
        "tier_used": "local",
    }


@pytest.fixture
def wrong_no_evidence_verdict() -> dict[str, Any]:
    """Wrong verdict with no evidence footprint.

    Previously this was hallucinated — now treated as wrong.
    The formatter shows it as WRONG, not a special label.
    """
    return {
        "claim": "Python was co-created by Elon Musk",
        "verdict": "wrong",
        "evidence": None,
        "source_url": None,
        "correction": (
            "Python was created by Guido van Rossum alone"
        ),
        "tier_used": "none",
    }


@pytest.fixture
def unverified_verdict() -> dict[str, Any]:
    """Sample unverified verdict."""
    return {
        "claim": "Python runs on the moon",
        "verdict": "unverified",
        "evidence": None,
        "source_url": None,
        "correction": None,
        "tier_used": "none",
    }


@pytest.fixture
def full_verdicts(
    verified_verdict: dict[str, Any],
    wrong_verdict: dict[str, Any],
    unverified_verdict: dict[str, Any],
) -> list[dict[str, Any]]:
    """Mixed verdict set used by report tests."""
    return [
        verified_verdict,
        wrong_verdict,
        unverified_verdict,
    ]


# ============================================================================
# _parse_verdict Tests
# ============================================================================

class TestParseVerdict:
    """Tests for raw verdict parsing."""

    def test_parses_valid_verified(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        verdict = _parse_verdict(verified_verdict)
        assert isinstance(verdict, Verdict)
        assert verdict.verdict == "verified"

    def test_parses_valid_wrong(
        self, wrong_verdict: dict[str, Any],
    ) -> None:
        verdict = _parse_verdict(wrong_verdict)
        assert verdict.verdict == "wrong"
        assert verdict.correction is not None

    def test_parses_valid_unverified(
        self, unverified_verdict: dict[str, Any],
    ) -> None:
        verdict = _parse_verdict(unverified_verdict)
        assert verdict.verdict == "unverified"

    def test_raises_on_missing_claim(self) -> None:
        with pytest.raises(ValueError, match="claim"):
            _parse_verdict({"verdict": "verified"})

    def test_raises_on_missing_verdict(self) -> None:
        with pytest.raises(ValueError, match="verdict"):
            _parse_verdict({"claim": "example"})

    def test_raises_on_unknown_verdict_type(self) -> None:
        with pytest.raises(ValueError, match="Unknown verdict type"):
            _parse_verdict({"claim": "example", "verdict": "maybe"})

    def test_defaults_tier_used_to_none(self) -> None:
        verdict = _parse_verdict(
            {"claim": "example", "verdict": "unverified"}
        )
        assert verdict.tier_used == "none"

    def test_optional_fields_default_to_none(self) -> None:
        verdict = _parse_verdict(
            {"claim": "example", "verdict": "verified"}
        )
        assert verdict.evidence is None
        assert verdict.source_url is None
        assert verdict.correction is None


# ============================================================================
# format_verdict Tests
# ============================================================================

class TestFormatVerdict:
    """Tests for individual verdict formatting."""

    def test_verified_contains_checkmark(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(verified_verdict)
        assert "✓" in output
        assert "VERIFIED" in output

    def test_verified_contains_claim(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(verified_verdict)
        assert "Guido van Rossum" in output

    def test_verified_contains_source(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(verified_verdict)
        assert "python.org" in output

    def test_wrong_contains_cross(
        self, wrong_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(wrong_verdict)
        assert "✗" in output
        assert "WRONG" in output

    def test_wrong_shows_claim_and_correction(
        self, wrong_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(wrong_verdict)
        assert "1989" in output
        assert "1991" in output

    def test_wrong_no_evidence_shows_as_wrong_not_hallucinated(
        self, wrong_no_evidence_verdict: dict[str, Any],
    ) -> None:
        """tier_used=none wrong verdict must show as WRONG.

        Per owner review — hallucinated label removed.
        No evidence footprint treated as wrong, not hallucinated.
        """
        output = format_verdict(wrong_no_evidence_verdict)
        assert "✗" in output
        assert "WRONG" in output
        assert "⚡" not in output
        assert "HALLUCINATED" not in output

    def test_unverified_contains_warning(
        self, unverified_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(unverified_verdict)
        assert "⚠" in output
        assert "UNVERIFIED" in output

    def test_unverified_reads_as_caution_not_failure(
        self, unverified_verdict: dict[str, Any],
    ) -> None:
        output = format_verdict(unverified_verdict)
        assert "caution" in output.lower()
        assert "error" not in output.lower()
        assert "failed" not in output.lower()

    def test_parse_error_handled_gracefully(self) -> None:
        output = format_verdict({"claim": "test"})
        assert "PARSE ERROR" in output

    def test_default_source_fallback(self) -> None:
        output = format_verdict(
            {"claim": "example", "verdict": "verified"}
        )
        assert "local knowledge base" in output

    def test_no_hallucinated_label_anywhere(
        self, wrong_no_evidence_verdict: dict[str, Any],
    ) -> None:
        """Confirm hallucinated label is gone from entire formatter."""
        output = format_verdict(wrong_no_evidence_verdict)
        assert "hallucinated" not in output.lower()


# ============================================================================
# format_report Tests
# ============================================================================

class TestFormatReport:
    """Tests for report generation."""

    def test_empty_verdicts_returns_message(self) -> None:
        output = format_report([])
        assert "No claims were identified" in output

    def test_report_contains_header(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        output = format_report(full_verdicts)
        assert "LOGIC LAYER" in output
        assert "VERIFICATION REPORT" in output

    def test_report_contains_summary_counts(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        output = format_report(full_verdicts)
        assert "1 verified" in output
        assert "1 wrong" in output
        assert "1 unverified" in output
        assert "3 total" in output

    def test_no_hallucinated_in_summary(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        """Summary must not contain hallucinated count.

        Per owner review — hallucinated verdict removed entirely.
        """
        output = format_report(full_verdicts)
        assert "hallucinated" not in output.lower()

    def test_wrong_section_before_verified(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        output = format_report(full_verdicts)
        wrong_pos    = output.index("WRONG CLAIMS")
        verified_pos = output.index("VERIFIED CLAIMS")
        assert wrong_pos < verified_pos

    def test_unverified_before_verified(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        output = format_report(full_verdicts)
        unverified_pos = output.index("UNVERIFIED CLAIMS")
        verified_pos   = output.index("VERIFIED CLAIMS")
        assert unverified_pos < verified_pos

    def test_section_header_is_wrong_claims_not_hallucinated(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        """Section header must be WRONG CLAIMS not WRONG / HALLUCINATED."""
        output = format_report(full_verdicts)
        assert "WRONG CLAIMS" in output
        assert "WRONG / HALLUCINATED CLAIMS" not in output

    def test_all_claims_present(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        output = format_report(full_verdicts)
        assert "Guido van Rossum" in output
        assert "1989" in output
        assert "moon" in output

    def test_single_verified_verdict(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        output = format_report([verified_verdict])
        assert "✓" in output

    def test_single_wrong_verdict(
        self, wrong_verdict: dict[str, Any],
    ) -> None:
        output = format_report([wrong_verdict])
        assert "✗" in output

    def test_single_unverified_verdict(
        self, unverified_verdict: dict[str, Any],
    ) -> None:
        output = format_report([unverified_verdict])
        assert "⚠" in output

    def test_all_verified_no_wrong_section(
        self, verified_verdict: dict[str, Any],
    ) -> None:
        output = format_report([verified_verdict])
        assert "WRONG CLAIMS" not in output
        assert "UNVERIFIED CLAIMS" not in output

    def test_returns_string(
        self, full_verdicts: list[dict[str, Any]],
    ) -> None:
        assert isinstance(format_report(full_verdicts), str)

    def test_no_print_statements(
        self, full_verdicts: list[dict[str, Any]], capsys,
    ) -> None:
        format_report(full_verdicts)
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_parse_error_section_added(self) -> None:
        output = format_report([{"claim": "broken"}])
        assert "PARSE ERRORS" in output