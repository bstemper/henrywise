"""Parsing of UK PAYE tax codes into a personal allowance."""

from __future__ import annotations

import re

# Trailing "emergency" (non-cumulative) marker: W1 (week 1), M1 (month 1), X.
_EMERGENCY = re.compile(r"\s*(W1|M1|X)$")


def parse_raw_string(raw: str) -> int:
    """Return the tax-free personal allowance (£) a UK PAYE tax code grants.

    Supports the numeric codes: ``1257L`` and friends (suffix L/M/N/T), plus
    ``0T`` (zero allowance).

    Emergency (non-cumulative) markers (``W1``/``M1``/``X``) are rejected. They
    tax each pay period in isolation with no year-end true-up: for even pay that
    lands on the same annual figure this tool computes, but we model bonuses in
    single months — exactly where a non-cumulative code diverges — so accepting
    one would imply a monthly split we can't stand behind.

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
    # A non-cumulative code would change the monthly split we report (and, with a
    # bonus, the annual total too), and we only model the cumulative basis.
    if _EMERGENCY.search(code):
        raise ValueError(
            f"Emergency (non-cumulative) codes aren't supported, got {raw!r}."
        )

    if code.startswith("K"):
        raise ValueError(f"K codes aren't supported, got {raw!r}.")
    match = re.fullmatch(r"(\d+)[LMNT]?", code)  # also matches "0T"
    if match:
        return int(match.group(1)) * 10
    raise ValueError(f"Unrecognised tax code {raw!r}.")
