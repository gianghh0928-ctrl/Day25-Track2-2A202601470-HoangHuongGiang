"""Pricing & purchasing economics — measure in $/1M-token, not $/GPU-hr.

Figures are June-2026 as-of snapshots from the deck's RESEARCH dossier; treat
live prices as fast-moving (re-baseline before each cohort).
"""
from __future__ import annotations


def request_cost(
    input_tok: int,
    output_tok: int,
    price_in_per_m: float,
    price_out_per_m: float,
    cached_in: int = 0,
    cache_discount: float = 0.10,   # Anthropic cached-read ~0.1x (=-90%)
    batch: bool = False,
    batch_discount: float = 0.50,   # Batch API ~ -50%
) -> float:
    """USD cost of a single request. Cached input billed at cache_discount x price."""
    cached_in = min(max(0, cached_in), input_tok)
    uncached_in = input_tok - cached_in
    cost = (
        (uncached_in / 1e6) * price_in_per_m
        + (cached_in / 1e6) * price_in_per_m * cache_discount
        + (output_tok / 1e6) * price_out_per_m
    )
    if batch:
        cost *= batch_discount
    return cost


def dollars_per_million(total_cost_usd: float, total_tokens: int) -> float:
    """Aggregate unit economics: $ per 1,000,000 tokens served."""
    if total_tokens <= 0:
        return 0.0
    return total_cost_usd / (total_tokens / 1e6)


def discount_stack(
    batch: bool = False,
    cache_hit_frac: float = 0.0,
    batch_discount: float = 0.50,
    cache_discount: float = 0.10,
) -> float:
    """Effective fraction of the naive bill after stacking discounts (input-heavy view).

    Discounts MULTIPLY: cache applies to the cached share of input, batch to the
    whole bill. batch + 100% cache-hit -> 0.5 * 0.1 = 0.05 (~95% off).
    """
    cache_mult = cache_hit_frac * cache_discount + (1.0 - cache_hit_frac)
    batch_mult = batch_discount if batch else 1.0
    return cache_mult * batch_mult


def break_even_utilization(discount_frac: float) -> float:
    """Utilization at which a commitment pays off ~= 1 - discount.

    A 45% reserved discount needs ~55% utilization (~13.2h/day) to beat on-demand.
    """
    return max(0.0, min(1.0, 1.0 - discount_frac))


def recommend_tier(hours_per_day: float, interruptible: bool, reserved_discount: float = 0.45) -> str:
    """Pick a purchasing tier from a workload's duty cycle + interruptibility.

    DOCUMENTED simple policy (instructor extension point — swap in your own):
      - interruptible & not 24/7  -> 'spot'      (checkpoint and ride the discount)
      - duty cycle >= break-even  -> 'reserved'  (steady, high utilization)
      - otherwise                 -> 'on_demand' (spiky / low duty)
    """
    duty = max(0.0, hours_per_day) / 24.0
    be = break_even_utilization(reserved_discount)
    if interruptible and hours_per_day < 24:
        return "spot"
    if duty >= be:
        return "reserved"
    return "on_demand"


def spot_checkpoint_cost(
    job_hours: float,
    spot_hr: float,
    on_demand_hr: float,
    interrupt_rate: float = 0.05,      # per-hour chance (H100 spot ~<5%)
    ckpt_overhead_frac: float = 0.03,  # steady cost of writing checkpoints
    rework_hours_per_interrupt: float = 0.5,
) -> dict:
    """Effective cost of running a checkpointable job on spot vs on-demand.

    Interruptions waste the compute since the last checkpoint (rework); checkpointing
    adds a small steady overhead. Spot still wins for interruptible jobs.
    """
    expected_interrupts = job_hours * interrupt_rate
    rework_hours = expected_interrupts * rework_hours_per_interrupt
    effective_hours = job_hours * (1.0 + ckpt_overhead_frac) + rework_hours
    spot_cost = effective_hours * spot_hr
    on_demand_cost = job_hours * on_demand_hr
    savings_pct = (1.0 - spot_cost / on_demand_cost) * 100.0 if on_demand_cost > 0 else 0.0
    return {
        "spot_effective_hours": round(effective_hours, 2),
        "spot_cost": round(spot_cost, 2),
        "on_demand_cost": round(on_demand_cost, 2),
        "savings_pct": round(savings_pct, 1),
    }


def recommend_tier_advanced(
    hours_per_day: float,
    interruptible: bool,
    on_demand_hr: float = 1.0,
    spot_hr: float = 0.3,
    interrupt_rate: float = 0.05,
    reserved_1yr_discount: float = 0.30,
    reserved_3yr_discount: float = 0.45,
) -> dict:
    """Advanced purchasing tier recommendation considering interruption rate and 1yr vs 3yr commitment.

    Extension 'Your Turn' #1:
    Compares effective costs for On-Demand, Spot (with rework), Reserved 1yr, and Reserved 3yr.
    """
    duty = max(0.0, hours_per_day) / 24.0
    on_demand_cost = hours_per_day * on_demand_hr
    res_1yr_cost = 24.0 * on_demand_hr * (1.0 - reserved_1yr_discount)
    res_3yr_cost = 24.0 * on_demand_hr * (1.0 - reserved_3yr_discount)

    if interruptible:
        ckpt_res = spot_checkpoint_cost(
            job_hours=hours_per_day,
            spot_hr=spot_hr,
            on_demand_hr=on_demand_hr,
            interrupt_rate=interrupt_rate,
        )
        spot_cost = ckpt_res["spot_cost"]
    else:
        spot_cost = float("inf")

    costs = {
        "on_demand": on_demand_cost,
        "spot": spot_cost,
        "reserved_1yr": res_1yr_cost,
        "reserved_3yr": res_3yr_cost,
    }

    best_tier = min(costs, key=costs.get)
    return {
        "recommended_tier": best_tier,
        "duty_cycle": round(duty, 3),
        "costs_24h": {k: round(v, 2) for k, v in costs.items() if v != float("inf")},
    }


def cache_is_worth_it(
    cache_hit_frac: float,
    min_hit_threshold: float = 0.20,
    cache_discount: float = 0.10,
    write_overhead_pct: float = 0.05,
) -> dict:
    """Evaluate whether prompt caching is economically beneficial based on cache read hit rate.

    Extension 'Your Turn' #3:
    Prompt caching saves money on reads but introduces write/storage overhead.
    """
    gross_savings = cache_hit_frac * (1.0 - cache_discount)
    net_savings = gross_savings - write_overhead_pct
    is_worth_it = cache_hit_frac >= min_hit_threshold and net_savings > 0

    return {
        "is_worth_it": is_worth_it,
        "cache_hit_frac": cache_hit_frac,
        "min_hit_threshold": min_hit_threshold,
        "net_savings_pct": round(max(0.0, net_savings) * 100.0, 1),
    }


def reasoning_cost_audit(token_df) -> dict:
    """Audit token usage and costs specifically for reasoning traffic.

    Extension 'Your Turn' #4:
    Calculates proportion of token volume consumed by reasoning workloads.
    """
    if "is_reasoning" not in token_df.columns:
        return {"reasoning_count": 0, "reasoning_token_share_pct": 0.0}

    reasoning_df = token_df[token_df["is_reasoning"] == True]
    reasoning_tokens = (reasoning_df["input_tokens"] + reasoning_df["output_tokens"]).sum() if len(reasoning_df) > 0 else 0
    total_tokens = (token_df["input_tokens"] + token_df["output_tokens"]).sum() if len(token_df) > 0 else 1

    return {
        "reasoning_request_count": len(reasoning_df),
        "total_request_count": len(token_df),
        "reasoning_token_share_pct": round((reasoning_tokens / total_tokens) * 100.0, 1),
    }

