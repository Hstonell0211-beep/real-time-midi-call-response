# Evaluation Integrity Audit

## Raw-AMT comparability

The legacy `amt_small_raw` path has mean `0.683141` because it applied style projection. True A0 raw has mean `0.560968`. The legacy label is superseded by the harmonized evaluation.

## Fallback semantics

A3 empty outputs: `0`. A4 empty outputs eligible for motif fallback: `0`. A4 motif fallback activations: `0`.
The A3-A4 comparison has `9000` exact zero differences among `9000` pairs. This is nonactivation, not evidence that replacement output was ineffective.
The previously reported 41.46% value is an event-repair sample rate (`0.414556`), not a phrase-level motif-fallback rate.

## Score decomposition

| variant | composite | style compliance | non-style structural |
| --- | ---: | ---: | ---: |
| A0 | 0.560968 | 0.563724 | 0.558971 |
| A1 | 0.574265 | 0.566740 | 0.579714 |
| A2 | 0.610704 | 0.561879 | 0.646061 |
| A3 | 0.640526 | 0.575326 | 0.687740 |
| A4 | 0.640526 | 0.575326 | 0.687740 |
| A5 | 0.708929 | 0.764076 | 0.668994 |
| A6 | 0.732610 | 0.809814 | 0.676704 |
