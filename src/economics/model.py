"""Fixed-volume baggage economics. All monetary inputs are scenario assumptions."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

HUNDRED = Decimal("100")
ZERO = Decimal("0")
MAX_REDUCTION_PCT = Decimal("50")


def nonnegative_decimal(value: Decimal | float | int | str, label: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"{label} must be a finite, nonnegative number") from error
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"{label} must be a finite, nonnegative number")
    return amount


def rounded(value: Decimal, places: str) -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Baseline:
    population: str
    start: str
    end: str
    target_months: tuple[str, ...]
    observed_months: tuple[str, ...]
    enplaned: int | None
    mishandled: int | None
    benchmark_rate: Decimal | None = None
    mixed_scope: bool = False

    def __post_init__(self) -> None:
        if (self.enplaned is None) != (self.mishandled is None):
            raise ValueError("Baseline counts must be jointly available")
        if self.enplaned is not None and not 0 <= self.mishandled <= self.enplaned:
            raise ValueError("Baseline counts must satisfy 0 ≤ mishandled ≤ enplaned")

    @property
    def rate(self) -> Decimal | None:
        return HUNDRED * Decimal(self.mishandled) / self.enplaned if self.enplaned else None

    @property
    def missing_months(self) -> tuple[str, ...]:
        return tuple(month for month in self.target_months if month not in self.observed_months)


@dataclass(frozen=True, init=False)
class Assumptions:
    cost_usd: Decimal
    reduction_pct: Decimal
    investment_usd: Decimal

    def __init__(self, cost_usd, reduction_pct, investment_usd=0):
        cost = nonnegative_decimal(cost_usd, "Cost per mishandled bag")
        reduction = nonnegative_decimal(reduction_pct, "Relative reduction")
        investment = nonnegative_decimal(investment_usd, "Implementation investment")
        if reduction > MAX_REDUCTION_PCT:
            raise ValueError("Relative reduction must be between 0 and 50 percent")
        object.__setattr__(self, "cost_usd", cost)
        object.__setattr__(self, "reduction_pct", reduction)
        object.__setattr__(self, "investment_usd", investment)


@dataclass(frozen=True)
class Projection:
    baseline: Baseline
    assumptions: Assumptions
    projected_rate: Decimal
    avoided_bags: Decimal
    remaining_bags: Decimal
    gross_usd: Decimal
    net_usd: Decimal
    benefit_cost_ratio: Decimal | None
    break_even_reduction_pct: Decimal | None

    def export_row(self, name: str) -> dict:
        baseline, inputs = self.baseline, self.assumptions
        return {
            "scenario": name,
            "population": baseline.population,
            "window_start": baseline.start,
            "window_end": baseline.end,
            "target_months": len(baseline.target_months),
            "observed_months": len(baseline.observed_months),
            "included_months": "|".join(baseline.observed_months),
            "mixed_reporting_scope": baseline.mixed_scope,
            "observed_bags_enplaned": baseline.enplaned,
            "observed_bags_mishandled": baseline.mishandled,
            "observed_rate_per_100": float(rounded(baseline.rate, "0.000001")),
            "assumed_cost_per_mishandled_bag_usd": float(rounded(inputs.cost_usd, "0.01")),
            "assumed_relative_reduction_pct": float(inputs.reduction_pct),
            "projected_rate_per_100": float(rounded(self.projected_rate, "0.000001")),
            "estimated_avoided_bags_expected": float(rounded(self.avoided_bags, "0.01")),
            "estimated_remaining_bags_expected": float(rounded(self.remaining_bags, "0.01")),
            "modeled_gross_avoided_cost_usd": float(rounded(self.gross_usd, "0.01")),
            "assumed_implementation_investment_usd": float(rounded(inputs.investment_usd, "0.01")),
            "modeled_net_after_entered_investment_usd": float(rounded(self.net_usd, "0.01")),
            "modeled_benefit_cost_ratio": (
                float(rounded(self.benefit_cost_ratio, "0.0001")) if self.benefit_cost_ratio is not None else None
            ),
        }


def project(baseline: Baseline, assumptions: Assumptions) -> Projection:
    rate = baseline.rate
    if rate is None:
        raise ValueError("Positive observed bag volume is required for a financial projection")
    relative = assumptions.reduction_pct / HUNDRED
    avoided = Decimal(baseline.mishandled) * relative
    gross = avoided * assumptions.cost_usd
    investment = assumptions.investment_usd
    maximum_recoverable = Decimal(baseline.mishandled) * assumptions.cost_usd
    return Projection(
        baseline, assumptions, rate * (1 - relative), avoided, Decimal(baseline.mishandled) - avoided,
        gross, gross - investment,
        gross / investment if investment else None,
        HUNDRED * investment / maximum_recoverable if investment and maximum_recoverable else None,
    )
