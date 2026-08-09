# Call100 Runtime Latency Logging and Scheduler Replay

## Design

- L0 preload off: inference starts at endpoint commit.
- L1 preload on: decoding may overlap the candidate-confirmation interval by up to `150 ms`.
- The logged inference timings come from actual local AMT decoding during the A6 full-controlled ablation runs.
- Endpoint-to-first-MIDI timing is a deterministic scheduler replay with the configured micro-buffer.

## Summary By Condition

| condition | sample_count | mean_latency_ms | p50_latency_ms | p95_latency_ms | p99_latency_ms | max_latency_ms | underrun_rate | mean_first_token_latency_ms | mean_total_generation_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L0_preload_off | 9000 | 161.302711 | 136.455450 | 323.520665 | 479.574320 | 815.510000 | 0.207444 | 81.302711 | 1655.312037 |
| L1_preload_on | 9000 | 91.720642 | 80.000000 | 173.520665 | 329.574320 | 665.510000 | 0.052444 | 81.302711 | 1655.312037 |

## Preload Comparison

| comparison | paired_sample_count | mean_latency_reduction_ms | ci95_low | ci95_high | positive_pairs | negative_pairs | tied_pairs | p_two_sided_sign_test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L1_preload_on_vs_L0_preload_off | 9000 | 69.582069 | 68.864876 | 70.263268 | 9000 | 0 | 0 | &lt;0.000001 |
