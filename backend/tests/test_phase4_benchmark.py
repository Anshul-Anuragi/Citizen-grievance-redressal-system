"""
Phase 4 Step 4: AI Pipeline Benchmark Unit & Regression Tests.

Covers:
  - At least 20 documented scenarios are present in benchmark dataset
  - Expected labels are explicit and match known evaluation types
  - Metric calculations (precision, recall, FPR, FNR) behave correctly
  - Zero-denominator cases return "N/A" rather than silently defaulting to 0 or 1
  - Per-type counts sum consistently to cumulative totals
  - Benchmark runs deterministically in isolation without network access
  - Emitted JSON report schema is valid and complete
"""

import pytest
import os
import json
from datetime import datetime, timezone

from scripts.evaluate_ai_pipeline import (
    build_benchmark_scenarios,
    calc_rate,
    execute_benchmark,
    EVALUATED_FINDING_TYPES,
    BENCHMARK_VERSION
)


def test_benchmark_has_at_least_20_scenarios():
    """Confirms at least 20 distinct synthetic scenarios are defined."""
    now = datetime.now(timezone.utc)
    scenarios = build_benchmark_scenarios(now)
    assert len(scenarios) >= 20, f"Expected >= 20 scenarios, found {len(scenarios)}"

    # Ensure unique scenario IDs
    scenario_ids = [s["id"] for s in scenarios]
    assert len(scenario_ids) == len(set(scenario_ids)), "Scenario IDs must be strictly unique"


def test_scenario_ground_truth_labels_are_valid():
    """Validates that all expected finding labels match defined evaluation finding types."""
    now = datetime.now(timezone.utc)
    scenarios = build_benchmark_scenarios(now)
    allowed_types = set(EVALUATED_FINDING_TYPES)

    for s in scenarios:
        assert "id" in s
        assert "description" in s
        assert "expected_findings" in s
        for exp in s["expected_findings"]:
            assert exp in allowed_types, f"Scenario {s['id']} has invalid expected type '{exp}'"


def test_calc_rate_zero_denominator_returns_na():
    """Explicitly verifies zero denominator returns 'N/A' rather than 0.0 or ZeroDivisionError."""
    assert calc_rate(0, 0) == "N/A"
    assert calc_rate(5, 0) == "N/A"
    assert calc_rate(10, 20) == 0.5
    assert calc_rate(1, 3) == 0.3333


def test_calc_rate_precision_and_rounding():
    """Checks rounding to 4 decimal places."""
    assert calc_rate(2, 3) == 0.6667
    assert calc_rate(4, 4) == 1.0


@pytest.mark.asyncio
async def test_benchmark_execution_and_metrics_consistency():
    """
    Executes the benchmark pipeline in-memory and verifies that:
      1. All 22 scenarios execute cleanly
      2. Cumulative TP, FP, FN, TN match the sum of per-type metrics
      3. Exact match accuracy is >= 95% for deterministic rules
      4. Report metadata is accurately populated
    """
    report = await execute_benchmark(enable_llm=False, workload_threshold=15, verbose=False)

    meta = report["benchmark_metadata"]
    assert meta["version"] == BENCHMARK_VERSION
    assert meta["total_scenarios_evaluated"] >= 20
    assert meta["execution_mode"] == "pure_deterministic_rules"

    agg = report["aggregate_metrics"]
    per_type = report["per_finding_type_metrics"]

    # Sum per-type counts
    sum_tp = sum(m["TP"] for m in per_type.values())
    sum_fp = sum(m["FP"] for m in per_type.values())
    sum_fn = sum(m["FN"] for m in per_type.values())
    sum_tn = sum(m["TN"] for m in per_type.values())

    cum = agg["cumulative_counts"]
    assert cum["TP"] == sum_tp
    assert cum["FP"] == sum_fp
    assert cum["FN"] == sum_fn
    assert cum["TN"] == sum_tn

    # High accuracy on deterministic synthetic set
    assert agg["exact_match_accuracy"] >= 0.95
    assert agg["micro_precision"] == 1.0
    assert agg["micro_recall"] == 1.0


@pytest.mark.asyncio
async def test_benchmark_json_serialization_and_stability(tmp_path):
    """
    Verifies that the generated benchmark report serializes cleanly to JSON
    with stable, expected dictionary keys and data types.
    """
    report = await execute_benchmark(enable_llm=False, workload_threshold=15, verbose=False)

    out_file = tmp_path / "benchmark_test_output.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    assert os.path.exists(out_file)
    with open(out_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert "benchmark_metadata" in loaded
    assert "aggregate_metrics" in loaded
    assert "per_finding_type_metrics" in loaded
    assert "scenario_results" in loaded
    assert len(loaded["scenario_results"]) == loaded["benchmark_metadata"]["total_scenarios_evaluated"]
