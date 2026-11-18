"""Deterministic interpretations and shared financial number formatting."""

from dataclasses import dataclass
from decimal import Decimal

from src.economics.model import MAX_REDUCTION_PCT, Projection, rounded


def money(value, compact: bool = False) -> str:
    amount = Decimal(str(value))
    sign = "−" if amount < 0 else ""
    amount = abs(amount)
    if compact:
        for divisor, suffix in ((1_000_000_000, "B"), (1_000_000, "M")):
            if amount >= divisor:
                return f"{sign}${amount / divisor:,.2f}{suffix}"
    precision = "0.01" if amount != amount.to_integral_value() and amount < 1_000 else "1"
    display = f"{rounded(amount, precision):,}"
    return f"{sign}${display}"


def whole_bags(value: Decimal) -> str:
    return f"{rounded(value, '1'):,}"


@dataclass(frozen=True)
class Insight:
    observation: str
    evidence: str
    interpretation: str
    next_step: str


def decision_brief(result: Projection) -> tuple[Insight, ...]:
    baseline, assumptions = result.baseline, result.assumptions
    if result.break_even_reduction_pct is None:
        break_even = (
            "Break-even needs a positive per-bag cost and reported mishandlings."
            if assumptions.investment_usd else "Add an investment estimate to assess break-even."
        )
    else:
        break_even = f"Break-even requires a {result.break_even_reduction_pct:.2f}% relative reduction."
        if result.break_even_reduction_pct > MAX_REDUCTION_PCT:
            break_even += " That exceeds the lab’s modeled range."

    if baseline.benchmark_rate is None:
        reference = f"The selected baseline covers {len(baseline.observed_months)} reported months."
    else:
        gap = baseline.rate - baseline.benchmark_rate
        if abs(gap) < Decimal("0.0005"):
            reference = "Its observed rate was approximately level with the same-month industry benchmark."
        else:
            position = "above" if gap > 0 else "below"
            reference = f"Its observed rate was {abs(gap):.3f} pp {position} the same-month industry benchmark."

    if assumptions.investment_usd == 0:
        financial_title = "Gross cost exposure"
        financial_evidence = f"The model estimates {money(result.gross_usd, compact=True)} in gross avoided cost."
        interpretation = "The scenario uses a zero investment input."
    elif result.net_usd < 0:
        financial_title = "Investment exceeds modeled benefit"
        financial_evidence = f"Modeled net benefit is {money(result.net_usd, compact=True)} after {money(assumptions.investment_usd, compact=True)} of investment."
        interpretation = "The entered investment exceeds the modeled gross avoided cost."
    else:
        financial_title = "Investment and modeled benefit"
        financial_evidence = f"Modeled net benefit is {money(result.net_usd, compact=True)} after {money(assumptions.investment_usd, compact=True)} of investment."
        interpretation = "The modeled benefit covers the entered investment under these assumptions."

    return (
        Insight(
            "Operational scale",
            f"A {assumptions.reduction_pct:g}% relative reduction would avoid about {whole_bags(result.avoided_bags)} mishandled bags at constant volume.",
            reference,
            "Use station and transfer records to define a pilot and measure its rate change against a comparable baseline.",
        ),
        Insight(financial_title, financial_evidence, interpretation, break_even),
        Insight(
            "Cost sensitivity",
            f"At this reduction, each additional $10 in assumed cost adds {money(result.avoided_bags * 10, compact=True)} to gross avoided cost.",
            "The assumed unit cost directly scales the modeled result.",
            "Estimate incremental cost per incident from claims and handling records with mutually exclusive cost categories.",
        ),
    )
