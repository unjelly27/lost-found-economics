"""Descriptive statistics on SQL-selected airline-month observations."""

import pandas as pd


def with_sample_standard_deviation(stability: pd.DataFrame) -> pd.DataFrame:
    """Convert the sample variance in squared percentage points to percentage points."""
    return stability.assign(sample_stddev_pp=stability["sample_variance_pp2"].astype(float).pow(0.5))


def volume_correlations(observations: pd.DataFrame) -> pd.DataFrame:
    """Return pooled and within-carrier-scope descriptive correlations."""
    within = observations.loc[observations["scope_observations"] > 1]
    comparisons = (
        ("pooled_pearson", observations, "bags_enplaned", "rate_per_100"),
        ("pooled_spearman", observations, "bags_enplaned", "rate_per_100"),
        ("within_carrier_scope_pearson", within, "enplaned_within_scope_difference",
         "rate_within_scope_difference_pp"),
    )
    rows = []
    for label, frame, volume_column, rate_column in comparisons:
        pairs = frame[[volume_column, rate_column]].dropna().astype(float)
        volumes, rates = pairs[volume_column], pairs[rate_column]
        if label == "pooled_spearman":
            volumes, rates = volumes.rank(), rates.rank()
        defined = len(pairs) >= 2 and volumes.nunique() > 1 and rates.nunique() > 1
        rows.append({
            "statistic": label,
            "observations": len(pairs),
            "correlation": float(volumes.corr(rates)) if defined else None,
        })
    return pd.DataFrame(rows)
