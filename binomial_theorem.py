#!/usr/bin/env python3
"""Expand (x·a + y·b)ⁿ with the binomial theorem.

    (x·a + y·b)ⁿ = Σ C(n, k) · xⁿ⁻ᵏ · yᵏ · aⁿ⁻ᵏ · bᵏ,   k = 0 … n

Every coefficient is exact. Integer and decimal multipliers give exact
decimals; any other fraction (1/3, -2/7, …) gives reduced fractions. There is
no limit on n besides time and memory, and the output is streamed, so even
expansions too large to fit in memory can be written to a file.

Usage:
    python binomial_theorem.py              # interactive mode
    python binomial_theorem.py 2 -3 5       # expands (2a - 3b)⁵
    python binomial_theorem.py 1/2 0.25 4   # fractions and decimals work too
"""

# Imports are kept cheap on purpose: for everyday sizes, starting Python is
# most of the running time, and argparse or fractions would each add to it
# noticeably.
from __future__ import annotations

import decimal
import os
import sys
from collections.abc import Iterator
from decimal import Decimal
from math import gcd

USAGE = """\
usage: binomial_theorem.py [x y n]

Expand (x·a + y·b)ⁿ with the binomial theorem, or ask for x, y and n
interactively when run without arguments. x and y may be integers, decimals
or fractions (3, -1.5, -2/3, 1e-3); n must be a whole number, 0 or more."""

# Big-integer arithmetic is done with Decimal integers rather than int. It is a
# little slower, but Decimal stores decimal digits, so converting a result to
# text is linear instead of quadratic, and for large n that conversion would
# dominate everything else. Inexact is trapped, so a lost digit raises instead
# of printing a wrong answer.
_EXACT = decimal.Context(
    prec=decimal.MAX_PREC,
    Emax=decimal.MAX_EMAX,
    Emin=decimal.MIN_EMIN,
    traps=[decimal.Inexact, decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow],
)
_SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")
_MIRROR_BUDGET = 1 << 25  # characters of coefficients kept for reuse (≈32 MB)

# An exact number as (numerator, denominator): reduced, denominator positive.
Ratio = tuple[int, int]
# A term of the expansion: (negative, |coefficient| as text, a exponent, b exponent).
Term = tuple[bool, str, int, int]


def superscript(n: int) -> str:
    return str(n).translate(_SUPERSCRIPT)


def _reduce(p: int, q: int) -> Ratio:
    if q < 0:
        p, q = -p, -q
    g = gcd(p, q)
    return p // g, q // g


def _ratio(value) -> Ratio:
    """Accept an int, Fraction, Decimal or (numerator, denominator) pair."""
    p, q = value if isinstance(value, tuple) else value.as_integer_ratio()
    return _reduce(p, q)


def parse_number(text: str) -> Ratio:
    """Parse an integer, decimal ("1.5", "1e3") or fraction ("2/3") exactly."""
    top, slash, bottom = text.partition("/")
    try:
        p, q = Decimal(top).as_integer_ratio()
        if slash:
            r, s = Decimal(bottom).as_integer_ratio()
            p, q = p * s, q * r
    except (ArithmeticError, ValueError):  # bad syntax, inf, nan
        q = 0
    if not q:
        raise ValueError(f"not a valid number: {text!r}")
    return _reduce(p, q)


def parse_exponent(text: str) -> int:
    try:
        n = int(text.strip())
    except ValueError:
        raise ValueError(f"'n' must be a whole number, got {text!r}") from None
    if n < 0:
        raise ValueError("'n' must not be negative")
    return n


def _decimal_places(den: int) -> int | None:
    """Decimal places needed to write 1/den exactly, or None if it repeats."""
    twos = (den & -den).bit_length() - 1
    den >>= twos
    fives = 0
    while den % 5 == 0:
        den //= 5
        fives += 1
    return max(twos, fives) if den == 1 else None


def _shift_point(digits: str, places: int) -> str:
    """Divide a string of digits by 10^places, dropping trailing zeros."""
    if not places:
        return digits
    digits = digits.zfill(places + 1)
    whole, frac = digits[:-places], digits[-places:].rstrip("0")
    return f"{whole}.{frac}" if frac else whole


def _decimal_magnitudes(lead: Ratio, other: Ratio, n: int) -> Iterator[str]:
    """Yield |C(n, k) · leadⁿ⁻ᵏ · otherᵏ| as decimals for k = 0, 1, …, n.

    Both values must have finite decimals. With lead = L/10ˢ and other = O/10ᵗ,
    term k is the integer Tₖ = C(n, k)·Lⁿ⁻ᵏ·Oᵏ shifted s(n-k) + tk places, and
    Tₖ₊₁ = Tₖ·(n-k)·O / ((k+1)·L) exactly, so each step is one multiplication
    and one division by a small number. Only the k = 0 term when other is 0.
    """
    (lp, lq), (op, oq) = lead, other
    s, t = _decimal_places(lq), _decimal_places(oq)
    scaled_lead, scaled_other = abs(lp) * 10**s // lq, abs(op) * 10**t // oq
    term = _EXACT.power(scaled_lead, n)
    yield _shift_point(str(term), s * n)
    if not scaled_other:
        return
    g = gcd(scaled_lead, scaled_other)
    up, down = scaled_other // g, scaled_lead // g
    for k in range(n):
        term = _EXACT.divide_int(_EXACT.multiply(term, (n - k) * up), (k + 1) * down)
        yield _shift_point(str(term), s * (n - k - 1) + t * (k + 1))


def _fraction_magnitudes(lead: Ratio, other: Ratio, n: int) -> Iterator[str]:
    """Yield |C(n, k) · leadⁿ⁻ᵏ · otherᵏ| as reduced "p/q" for k = 0, 1, …, n.

    Each term is the previous one times (n-k)·other / ((k+1)·lead). Since the
    running fraction is already reduced, it only needs gcds against that small
    factor, never a gcd of two huge numbers. Only the k = 0 term when other is 0.
    """
    (lp, lq), (op, oq) = lead, other
    num, den = _EXACT.power(abs(lp), n), _EXACT.power(lq, n)
    yield f"{num}/{den}" if den != 1 else str(num)
    if not op:
        return
    rp, rq = _reduce(abs(op) * lq, oq * abs(lp))
    for k in range(n):
        up, down = _reduce((n - k) * rp, (k + 1) * rq)
        g_num = gcd(int(_EXACT.remainder(num, down)), down) if down > 1 else 1
        g_den = gcd(int(_EXACT.remainder(den, up)), up) if up > 1 else 1
        if g_num > 1:
            num = _EXACT.divide_int(num, g_num)
        if g_den > 1:
            den = _EXACT.divide_int(den, g_den)
        if up > g_den:
            num = _EXACT.multiply(num, up // g_den)
        if down > g_num:
            den = _EXACT.multiply(den, down // g_num)
        yield f"{num}/{den}" if den != 1 else str(num)


def _mirrored(magnitudes: Iterator[str], n: int) -> Iterator[str]:
    """When |x| = |y| term n - k equals term k, so reuse the first half.

    Only the first _MIRROR_BUDGET characters are kept, so memory stays bounded
    however large n gets; terms past that are computed as usual.
    """
    kept: list[str] = []
    size = 0
    for k in range(n + 1):
        if n - k < len(kept):
            yield kept[n - k]
            continue
        magnitude = next(magnitudes)
        if k < n - k and size < _MIRROR_BUDGET:
            kept.append(magnitude)
            size += len(magnitude)
        yield magnitude


def terms(x, y, n: int) -> Iterator[Term]:
    """Yield the non-zero terms of (x·a + y·b)ⁿ, from aⁿ down to bⁿ.

    x and y may be ints, Fractions, Decimals or (numerator, denominator) pairs.
    """
    if n < 0:
        raise ValueError("'n' must not be negative")
    x, y = _ratio(x), _ratio(y)
    (xp, xq), (yp, yq) = x, y
    if not xp and not yp:
        if n == 0:
            raise ValueError("0⁰ is undefined")
        return

    exact = _decimal_places(xq) is not None and _decimal_places(yq) is not None
    magnitudes = _decimal_magnitudes if exact else _fraction_magnitudes
    if not xp:
        ks, mags = (n,), magnitudes(y, x, n)
    elif not yp:
        ks, mags = (0,), magnitudes(x, y, n)
    elif (abs(xp), xq) == (abs(yp), yq):
        ks, mags = range(n + 1), _mirrored(magnitudes(x, y, n), n)
    else:
        ks, mags = range(n + 1), magnitudes(x, y, n)

    for k, magnitude in zip(ks, mags):
        negative = (xp < 0 and (n - k) % 2 == 1) != (yp < 0 and k % 2 == 1)
        yield negative, magnitude, n - k, k


def _variable(name: str, exp: int) -> str:
    if exp == 0:
        return ""
    return name if exp == 1 else name + superscript(exp)


def expansion(x, y, n: int) -> Iterator[str]:
    """Yield the text of (x·a + y·b)ⁿ expanded, in pieces.

    Coefficients are yielded on their own, apart from the superscripts, so the
    long runs of digits stay plain ASCII strings that are cheap to write out.
    """
    first = True
    for negative, magnitude, a_exp, b_exp in terms(x, y, n):
        if first:
            yield "-" if negative else ""
            first = False
        else:
            yield " - " if negative else " + "
        variables = _variable("a", a_exp) + _variable("b", b_exp)
        if variables:
            if magnitude == "1":
                magnitude = ""
            elif "/" in magnitude:
                magnitude = f"({magnitude})"
        yield magnitude
        yield variables
    if first:
        yield "0"


def solution(x, y, n: int) -> Iterator[str]:
    """Yield the full "(xa + yb)ⁿ = …" line, in pieces."""
    x, y = _ratio(x), _ratio(y)
    base = "".join(expansion(x, y, 1))
    yield f"({base}){superscript(n)} = "
    if n == 0:
        yield f"1   (for {base} ≠ 0)" if x[0] or y[0] else "undefined (0⁰)"
    else:
        yield from expansion(x, y, n)


def solve(x, y, n: int) -> str:
    """Return the full "(xa + yb)ⁿ = …" line."""
    return "".join(solution(x, y, n))


def interactive() -> None:
    print("Binomial theorem: expands (x·a + y·b)ⁿ  — press Ctrl+C to quit\n")
    while True:
        try:
            x = parse_number(input("Enter 'a' multiplier (x): "))
            y = parse_number(input("Enter 'b' multiplier (y): "))
            n = parse_exponent(input("Enter n: "))
        except ValueError as exc:
            print(f"Input error: {exc}\n")
            continue
        print()
        sys.stdout.writelines(solution(x, y, n))
        print()
        if input("\nAgain? [Y/n]: ").strip().lower() in {"n", "no", "q", "quit"}:
            break
        print()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if {"-h", "--help"} & set(args):
        print(USAGE)
        return 0
    if not args:
        try:
            interactive()
        except (KeyboardInterrupt, EOFError):
            print()
        return 0

    try:
        if len(args) != 3:
            raise ValueError("give all of x, y and n, or none for interactive mode")
        x, y, n = parse_number(args[0]), parse_number(args[1]), parse_exponent(args[2])
    except ValueError as exc:
        print(f"{USAGE.splitlines()[0]}\nerror: {exc}", file=sys.stderr)
        return 2

    try:
        sys.stdout.writelines(solution(x, y, n))
        sys.stdout.write("\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Output was cut short (e.g. piped into `head`); exit quietly.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
