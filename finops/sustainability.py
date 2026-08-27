"""Sustainability economics — energy and carbon as governed cost levers (deck §11).

Region selection cuts $ and carbon together; reasoning queries are an energy bomb.
"""
from __future__ import annotations

# Grid carbon intensity (gCO2 / kWh) — illustrative 2026 snapshot.
REGION_CARBON = {
    "us-east-1": 380,
    "us-west-2": 120,   # Oregon hydro
    "europe-north1": 30,  # Norway
    "europe-central2": 660,  # Poland (dirtiest)
    "us-east-wa": 90,
}
# Electricity price (USD / kWh) — illustrative.
REGION_PRICE_KWH = {
    "us-east-1": 0.12,
    "us-west-2": 0.07,
    "europe-north1": 0.09,
    "europe-central2": 0.18,
    "us-east-wa": 0.055,
}

REASONING_ENERGY_MULTIPLIER = 80.0  # deck: reasoning ~74-86x a small-model query


def wh_per_query(total_tokens: int, wh_per_1k_tokens: float = 0.30, is_reasoning: bool = False) -> float:
    """Energy for one query. Median Gemini prompt ~0.24 Wh; reasoning ~74-86x."""
    base = (total_tokens / 1000.0) * wh_per_1k_tokens
    return base * (REASONING_ENERGY_MULTIPLIER if is_reasoning else 1.0)


def carbon_g(wh: float, region: str = "us-east-1") -> float:
    """Grams CO2 for an energy amount in a region."""
    gco2_kwh = REGION_CARBON.get(region, 400)
    return (wh / 1000.0) * gco2_kwh


def energy_cost_usd(wh: float, region: str = "us-east-1") -> float:
    """Electricity cost of an energy amount in a region."""
    return (wh / 1000.0) * REGION_PRICE_KWH.get(region, 0.12)


def tokens_per_watt(total_tokens: int, wh: float, seconds: float = 1.0) -> float:
    """Energy efficiency of serving: tokens per watt (higher is better)."""
    watts = (wh * 3600.0) / seconds if seconds > 0 else 0.0
    return total_tokens / watts if watts > 0 else 0.0


def carbon_aware_schedule(workload_df, default_region: str = "us-east-1", green_region: str = "europe-north1") -> dict:
    """Extension 'Your Turn' #5: Carbon-aware scheduling.

    Calculates total energy & carbon emissions if interruptible workloads are
    shifted from default region to a green region with hydro/nuclear power.
    """
    if len(workload_df) == 0:
        return {"carbon_saved_g": 0.0, "carbon_savings_pct": 0.0}

    total_default_carbon = 0.0
    total_green_carbon = 0.0

    for _, row in workload_df.iterrows():
        num_gpus = row.get("num_gpus", 1)
        hours = row.get("hours_per_day", 24) * row.get("days", 1)
        watts = 400.0
        kwh = (num_gpus * watts * hours) / 1000.0

        is_interruptible = row.get("interruptible", False)
        dest_region = green_region if is_interruptible else default_region

        total_default_carbon += (kwh * REGION_CARBON.get(default_region, 380))
        total_green_carbon += (kwh * REGION_CARBON.get(dest_region, 380))

    carbon_saved = total_default_carbon - total_green_carbon
    savings_pct = (carbon_saved / total_default_carbon * 100.0) if total_default_carbon > 0 else 0.0

    return {
        "default_region": default_region,
        "green_region": green_region,
        "default_carbon_g": round(total_default_carbon, 2),
        "optimized_carbon_g": round(total_green_carbon, 2),
        "carbon_saved_g": round(carbon_saved, 2),
        "carbon_savings_pct": round(savings_pct, 1),
    }

