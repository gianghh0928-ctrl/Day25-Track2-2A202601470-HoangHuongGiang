import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finops import pricing, sustainability


def test_recommend_tier_advanced():
    # Interruptible workload with 4h duty cycle -> recommend spot
    res_spot = pricing.recommend_tier_advanced(hours_per_day=4, interruptible=True)
    assert res_spot["recommended_tier"] == "spot"

    # Non-interruptible 24h heavy workload -> recommend reserved_3yr
    res_res = pricing.recommend_tier_advanced(hours_per_day=24, interruptible=False)
    assert res_res["recommended_tier"] in ["reserved_3yr", "reserved_1yr"]

    # Low duty cycle non-interruptible workload -> recommend on_demand
    res_od = pricing.recommend_tier_advanced(hours_per_day=2, interruptible=False)
    assert res_od["recommended_tier"] == "on_demand"


def test_cache_is_worth_it():
    # 50% cache hit rate with default settings -> worth it
    res_good = pricing.cache_is_worth_it(cache_hit_frac=0.50)
    assert res_good["is_worth_it"] is True
    assert res_good["net_savings_pct"] > 0

    # 10% hit rate below minimum threshold -> not worth it
    res_bad = pricing.cache_is_worth_it(cache_hit_frac=0.10)
    assert res_bad["is_worth_it"] is False


def test_reasoning_cost_audit():
    df = pd.DataFrame([
        {"input_tokens": 100, "output_tokens": 500, "is_reasoning": True},
        {"input_tokens": 200, "output_tokens": 200, "is_reasoning": False},
    ])
    res = pricing.reasoning_cost_audit(df)
    assert res["reasoning_request_count"] == 1
    assert res["total_request_count"] == 2
    assert res["reasoning_token_share_pct"] == 60.0


def test_carbon_aware_schedule():
    df = pd.DataFrame([
        {"num_gpus": 2, "hours_per_day": 12, "days": 1, "interruptible": True},
        {"num_gpus": 4, "hours_per_day": 24, "days": 1, "interruptible": False},
    ])
    res = sustainability.carbon_aware_schedule(df, default_region="us-east-1", green_region="europe-north1")
    assert res["carbon_saved_g"] > 0
    assert res["carbon_savings_pct"] > 0
