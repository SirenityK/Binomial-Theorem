import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal
from fractions import Fraction
from math import comb, gcd
from unittest import mock

import binomial_theorem as bt

F = Fraction
VALUES = [F(0), F(1), F(-1), F(2), F(-3), F("0.5"), F("-0.5"), F("-0.25"), F("1.5"),
          F("0.1"), F("12.5"), F(3, 4), F(1, 3), F(-1, 3), F(-2, 7), F(5, 6)]


def reference(x, y, n):
    """(x·a + y·b)ⁿ by repeated polynomial multiplication: slow but obviously right."""
    coeffs = [F(1)]
    for _ in range(n):
        new = [F(0)] * (len(coeffs) + 1)
        for k, c in enumerate(coeffs):
            new[k] += c * x
            new[k + 1] += c * y
        coeffs = new
    return [(c, n - k, k) for k, c in enumerate(coeffs) if c]


def terminates(value):
    return bt._decimal_places(F(value).denominator) is not None


class TermsTest(unittest.TestCase):
    def check_style(self, magnitude, decimals):
        if decimals:
            self.assertNotIn("/", magnitude)
            if "." in magnitude:
                whole, frac = magnitude.split(".")
                self.assertFalse(frac.endswith("0"), magnitude)
            else:
                whole = magnitude
            self.assertTrue(whole == "0" or not whole.startswith("0"), magnitude)
        elif "/" in magnitude:
            p, q = map(int, magnitude.split("/"))
            self.assertGreater(q, 1)
            self.assertEqual(gcd(p, q), 1, magnitude)
        else:
            self.assertTrue(magnitude.isdigit(), magnitude)

    def test_matches_polynomial_multiplication(self):
        for x in VALUES:
            for y in VALUES:
                decimals = terminates(x) and terminates(y)
                for n in range(10):
                    if not x and not y and n == 0:
                        continue
                    with self.subTest(x=x, y=y, n=n):
                        got = []
                        for negative, magnitude, a_exp, b_exp in bt.terms(x, y, n):
                            self.check_style(magnitude, decimals)
                            value = F(magnitude) * (-1 if negative else 1)
                            got.append((value, a_exp, b_exp))
                        self.assertEqual(got, reference(x, y, n))

    def test_large_n_closed_form(self):
        cases = [(F(2), F(-3), 400), (F("0.5"), F("1.25"), 300), (F(1, 3), F(-2, 7), 250),
                 (F(-7), F(7), 301), (F(2, 3), F(-2, 3), 200)]
        for x, y, n in cases:
            with self.subTest(x=x, y=y, n=n):
                for k, (negative, magnitude, a_exp, b_exp) in enumerate(bt.terms(x, y, n)):
                    expected = comb(n, k) * x ** (n - k) * y**k
                    self.assertEqual(F(magnitude) * (-1 if negative else 1), expected)
                    self.assertEqual((a_exp, b_exp), (n - k, k))

    def test_mirroring_past_its_memory_budget(self):
        for x, y in ((F(-3, 2), F(3, 2)), (F(2, 3), F(-2, 3))):
            for budget in (0, 1, 15, 40):
                for n in (7, 8, 30):
                    with self.subTest(x=x, y=y, budget=budget, n=n), \
                            mock.patch.object(bt, "_MIRROR_BUDGET", budget):
                        got = [F(m) * (-1 if neg else 1) for neg, m, _, _ in bt.terms(x, y, n)]
                        self.assertEqual(got, [c for c, _, _ in reference(x, y, n)])

    def test_beyond_int_str_digit_limit(self):
        # Coefficients here have far more than 4300 digits, which str(int) refuses.
        n = 12000
        terms = list(bt.terms(2, 3, n))
        self.assertEqual(len(terms), n + 1)
        for k in (0, 1, n // 3, n // 2, n):
            self.assertEqual(Decimal(terms[k][1]), Decimal(comb(n, k) * 2 ** (n - k) * 3**k))

    def test_zero_to_the_zero_is_undefined(self):
        with self.assertRaises(ValueError):
            list(bt.terms(0, 0, 0))

    def test_negative_exponent_is_rejected(self):
        with self.assertRaises(ValueError):
            list(bt.terms(1, 1, -1))


class FormatTest(unittest.TestCase):
    def test_accepts_other_number_types(self):
        expected = "(0.5a - 3b)² = 0.25a² - 3ab + 9b²"
        self.assertEqual(bt.solve(F(1, 2), -3, 2), expected)
        self.assertEqual(bt.solve(Decimal("0.50"), Decimal(-3), 2), expected)
        self.assertEqual(bt.solve((2, 4), (6, -2), 2), expected)

    def test_solve(self):
        cases = {
            (1, 1, 5): "(a + b)⁵ = a⁵ + 5a⁴b + 10a³b² + 10a²b³ + 5ab⁴ + b⁵",
            (1, -1, 3): "(a - b)³ = a³ - 3a²b + 3ab² - b³",
            (2, -3, 4): "(2a - 3b)⁴ = 16a⁴ - 96a³b + 216a²b² - 216ab³ + 81b⁴",
            (-1, -1, 2): "(-a - b)² = a² + 2ab + b²",
            (F("0.1"), F("0.2"), 2): "(0.1a + 0.2b)² = 0.01a² + 0.04ab + 0.04b²",
            (F(1, 2), F("0.25"), 3):
                "(0.5a + 0.25b)³ = 0.125a³ + 0.1875a²b + 0.09375ab² + 0.015625b³",
            (F(-1, 3), 1, 2): "(-(1/3)a + b)² = (1/9)a² - (2/3)ab + b²",
            (F(1, 3), F(1, 2), 2): "((1/3)a + (1/2)b)² = (1/9)a² + (1/3)ab + (1/4)b²",
            (F(1, 3), 3, 2): "((1/3)a + 3b)² = (1/9)a² + 2ab + 9b²",
            (F("1.5"), 0, 3): "(1.5a)³ = 3.375a³",
            (0, -2, 3): "(-2b)³ = -8b³",
            (0, 0, 3): "(0)³ = 0",
            (0, 0, 0): "(0)⁰ = undefined (0⁰)",
            (2, 3, 0): "(2a + 3b)⁰ = 1   (for 2a + 3b ≠ 0)",
            (-1, 2, 1): "(-a + 2b)¹ = -a + 2b",
            (5, 5, 10): "(5a + 5b)¹⁰ = " + " + ".join(
                f"{comb(10, k) * 5**10}" + ("a" + bt.superscript(10 - k) if k < 9 else "a" if k == 9 else "")
                + ("b" + bt.superscript(k) if k > 1 else "b" if k == 1 else "")
                for k in range(11)),
        }
        for (x, y, n), expected in cases.items():
            with self.subTest(x=x, y=y, n=n):
                self.assertEqual(bt.solve(F(x), F(y), n), expected)

    def test_shift_point(self):
        self.assertEqual(bt._shift_point("12345", 0), "12345")
        self.assertEqual(bt._shift_point("12345", 2), "123.45")
        self.assertEqual(bt._shift_point("12300", 2), "123")
        self.assertEqual(bt._shift_point("12310", 2), "123.1")
        self.assertEqual(bt._shift_point("5", 3), "0.005")
        self.assertEqual(bt._shift_point("50", 2), "0.5")


class ParseTest(unittest.TestCase):
    def test_numbers(self):
        self.assertEqual(bt.parse_number(" 3 "), (3, 1))
        self.assertEqual(bt.parse_number("-1.25"), (-5, 4))
        self.assertEqual(bt.parse_number("2/6"), (1, 3))
        self.assertEqual(bt.parse_number(" 2 / -6 "), (-1, 3))
        self.assertEqual(bt.parse_number("1.5/2"), (3, 4))
        self.assertEqual(bt.parse_number("1e3"), (1000, 1))
        self.assertEqual(bt.parse_number("-0"), (0, 1))
        for bad in ("", "abc", "1/0", "1,5", "inf", "-inf", "nan", "/3", "1/", "1/2/3", "0x10"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bt.parse_number(bad)

    def test_exponent(self):
        self.assertEqual(bt.parse_exponent(" 7 "), 7)
        for bad in ("-1", "1.5", "x", ""):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                bt.parse_exponent(bad)


class CliTest(unittest.TestCase):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = bt.main(list(argv))
            except SystemExit as exc:
                code = exc.code
        return code, out.getvalue(), err.getvalue()

    def test_arguments(self):
        self.assertEqual(self.run_main("2", "-3", "2"), (0, "(2a - 3b)² = 4a² - 12ab + 9b²\n", ""))

    def test_negative_numbers_are_not_options(self):
        code, out, _ = self.run_main("-1/2", "-1e1", "1")
        self.assertEqual((code, out), (0, "(-0.5a - 10b)¹ = -0.5a - 10b\n"))

    def test_help(self):
        code, out, _ = self.run_main("-h")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("usage:"))

    def test_bad_arguments(self):
        for argv in (["1", "2"], ["1", "2", "3", "4"], ["1", "2", "-3"], ["x", "2", "3"], ["1", "2", "1.5"]):
            with self.subTest(argv=argv):
                code, out, err = self.run_main(*argv)
                self.assertEqual((code, out), (2, ""))
                self.assertIn("error", err)

    def test_interactive(self):
        answers = ["1", "x", "1", "1", "2", "", "2", "0", "3", "n"]
        with mock.patch("builtins.input", side_effect=answers):
            code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("Input error", out)
        self.assertIn("(a + b)² = a² + 2ab + b²", out)
        self.assertIn("(2a)³ = 8a³", out)

    def test_interactive_eof(self):
        with mock.patch("builtins.input", side_effect=EOFError):
            self.assertEqual(self.run_main()[0], 0)


if __name__ == "__main__":
    unittest.main()
