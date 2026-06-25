"""
Verdict Formatting Layer.

This module converts raw verification results produced by the
verification orchestrator into structured, human-readable CLI output.

Responsibilities:
    - Validate incoming verdict dictionaries.
    - Convert dictionaries into strongly typed Verdict objects.
    - Format individual verdicts.
    - Generate complete verification reports.

The formatter is presentation-only and contains no verification logic.

Note:
    Hallucinated verdict type has been removed per owner review.
    Claims with no evidence footprint are treated as unverified
    since we cannot prove hallucination with certainty.

Usage (by Anay in orchestrator.py):
    from logiclayer.reporting.formatter import format_report

    verdicts = run_verification(raw_response)
    print(format_report(verdicts))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Verdict:
    """Structured representation of a single claim verdict.

    Attributes:
        claim:
            The atomic factual claim that was checked.
        verdict:
            One of: verified, wrong, unverified
        evidence:
            Evidence supporting or contradicting the claim.
        source_url:
            URL of the source providing evidence.
        correction:
            Correct statement for wrong claims.
        tier_used:
            Verification tier that produced the result.
            "none" indicates no tier found evidence.
    """

    claim: str
    verdict: str
    evidence: Optional[str] = None
    source_url: Optional[str] = None
    correction: Optional[str] = None
    tier_used: str = "none"


def _parse_verdict(raw: Mapping[str, Any]) -> Verdict:
    """Convert a raw verdict dictionary into a Verdict object.

    Args:
        raw: Raw verdict dictionary containing at minimum
            'claim' and 'verdict'.

    Returns:
        Parsed Verdict instance.

    Raises:
        ValueError: If required fields are missing or verdict
            type is invalid.
    """
    required_fields = ("claim", "verdict")

    for field_name in required_fields:
        if not raw.get(field_name):
            raise ValueError(
                f"Verdict missing required field: "
                f"'{field_name}'. Got: {raw}"
            )

    valid_verdicts = {"verified", "wrong", "unverified"}

    if raw["verdict"] not in valid_verdicts:
        raise ValueError(
            f"Unknown verdict type: '{raw['verdict']}'. "
            f"Expected one of {sorted(valid_verdicts)}"
        )

    return Verdict(
        claim=str(raw["claim"]),
        verdict=str(raw["verdict"]),
        evidence=raw.get("evidence"),
        source_url=raw.get("source_url"),
        correction=raw.get("correction"),
        tier_used=str(raw.get("tier_used", "none")),
    )


def _format_verified(verdict: Verdict) -> str:
    """Format a verified verdict for CLI output."""
    source = verdict.source_url or "local knowledge base"
    evidence = verdict.evidence or "matched local fact"

    return "\n".join([
        "  ✓  VERIFIED",
        f"     Claim    : {verdict.claim}",
        f"     Evidence : {evidence}",
        f"     Source   : {source}",
    ])


def _format_wrong(verdict: Verdict) -> str:
    """Format an incorrect verdict for CLI output."""
    correct = (
        verdict.correction
        or verdict.evidence
        or "see source"
    )
    source = verdict.source_url or "local knowledge base"

    return "\n".join([
        "  ✗  WRONG",
        f"     AI said  : {verdict.claim}",
        f"     Truth    : {correct}",
        f"     Source   : {source}",
    ])


def _format_unverified(verdict: Verdict) -> str:
    """Format an unverified verdict for CLI output.

    Note:
        This also covers cases where no evidence footprint
        exists. Per owner review, we cannot prove hallucination
        with certainty so unverified is the honest label.
    """
    return "\n".join([
        "  ⚠  UNVERIFIED",
        f"     Claim    : {verdict.claim}",
        (
            "     Status   : No evidence found in local "
            "database or trusted sources."
        ),
        (
            "     Action   : Treat this claim with caution "
            "and verify independently."
        ),
    ])


def format_verdict(raw: Mapping[str, Any]) -> str:
    """Format a single verdict dictionary.

    Args:
        raw: Raw verdict dictionary.

    Returns:
        Human-readable verdict block.
    """
    try:
        verdict = _parse_verdict(raw)
    except ValueError as error:
        logger.error("Failed to parse verdict: %s", error)
        return f"  ?  PARSE ERROR: {error}"

    match verdict.verdict:
        case "verified":
            return _format_verified(verdict)
        case "wrong":
            return _format_wrong(verdict)
        case "unverified":
            return _format_unverified(verdict)
        case _:
            return (
                "  ?  UNKNOWN VERDICT TYPE "
                f"({verdict.verdict})"
            )


def format_report(
    verdicts: list[Mapping[str, Any]],
) -> str:
    """Generate a complete verification report.

    Report ordered by urgency:
        1. Wrong claims
        2. Unverified claims
        3. Verified claims

    Args:
        verdicts: Collection of raw verdict dictionaries.

    Returns:
        Fully formatted CLI report.
    """
    wide = "━" * 56
    sep = "─" * 56

    if not verdicts:
        logger.warning(
            "format_report called with empty verdict list"
        )
        return (
            f"\n{wide}\n"
            f"  LOGIC LAYER — VERIFICATION REPORT\n"
            f"{wide}\n"
            f"  No claims were identified in the response.\n"
            f"{wide}"
        )

    parsed_verdicts: list[Verdict] = []
    parse_errors: list[str] = []

    for raw in verdicts:
        try:
            parsed_verdicts.append(_parse_verdict(raw))
        except ValueError as error:
            logger.error("Skipping malformed verdict: %s", error)
            parse_errors.append(str(error))

    verified   = [v for v in parsed_verdicts if v.verdict == "verified"]
    wrong      = [v for v in parsed_verdicts if v.verdict == "wrong"]
    unverified = [v for v in parsed_verdicts if v.verdict == "unverified"]
    total      = len(parsed_verdicts)

    summary = "  " + "  |  ".join([
        f"{len(verified)} verified",
        f"{len(wrong)} wrong",
        f"{len(unverified)} unverified",
        f"{total} total",
    ])

    sections: list[str] = []

    if wrong:
        sections.extend(["WRONG CLAIMS", sep])
        for verdict in wrong:
            sections.append(_format_wrong(verdict))
            sections.append("")

    if unverified:
        sections.extend(["UNVERIFIED CLAIMS", sep])
        for verdict in unverified:
            sections.append(_format_unverified(verdict))
            sections.append("")

    if verified:
        sections.extend(["VERIFIED CLAIMS", sep])
        for verdict in verified:
            sections.append(_format_verified(verdict))
            sections.append("")

    if parse_errors:
        sections.extend(["PARSE ERRORS", sep])
        for error in parse_errors:
            sections.append(f"  ?  {error}")
            sections.append("")

    output_lines = [
        "", wide,
        "  LOGIC LAYER — VERIFICATION REPORT",
        wide, summary, wide, "",
        *sections, wide,
    ]

    logger.info(
        "Report formatted: %d total, %d wrong, "
        "%d unverified, %d verified",
        total, len(wrong), len(unverified), len(verified),
    )

    return "\n".join(output_lines)