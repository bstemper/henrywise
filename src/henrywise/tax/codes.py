"""Parsing of UK PAYE tax codes into a personal allowance."""

from __future__ import annotations

import re

# Trailing "emergency" (non-cumulative) marker — irrelevant to an annual total.
_EMERGENCY = re.compile(r"\s*(W1|M1|X)$")


def parse_tax_code(raw: str) -> int:
    """Return the tax-free personal allowance (£) a UK PAYE tax code grants.

    Supports the numeric codes: ``1257L`` and friends (suffix L/M/N/T), plus
    ``0T`` (zero allowance). A trailing emergency marker (``W1``/``M1``/``X``)
    is accepted but ignored.

    Region-prefixed codes (``S`` for Scotland, ``C`` for Wales) are rejected:
    Scotland has its own bands and rates that this calculator doesn't model,
    so accepting one would silently apply the wrong (rest-of-UK) tax.

    K codes (a negative allowance) and the whole-regime codes (NT, BR, D0, D1)
    are not supported.
    """
    code = raw.strip().upper()
    if not code:
        raise ValueError("Tax code is empty.")

    # A region prefix means a tax regime we don't model — refuse rather than
    # silently taxing a Scottish/Welsh code at rest-of-UK rates.
    if code[0] in ("S", "C") and len(code) > 1:
        raise ValueError(f"Region-prefixed codes aren't supported, got {raw!r}.")
    # Drop a non-cumulative "emergency" marker; it doesn't change the year's total.
    code = _EMERGENCY.sub("", code).strip()

    if code.startswith("K"):
        raise ValueError(f"K codes aren't supported, got {raw!r}.")
    match = re.fullmatch(r"(\d+)[LMNT]?", code)  # also matches "0T"
    if match:
        return int(match.group(1)) * 10
    raise ValueError(f"Unrecognised tax code {raw!r}.")
