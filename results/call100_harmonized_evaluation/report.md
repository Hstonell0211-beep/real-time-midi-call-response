# Harmonized Call100 Candidate Evaluation

The raw and controlled AMT conditions reuse the exact A0 and A6 batches from the module ablation. The motif batch is retained from the rule-based run, and all 27,000 MIDI files are re-scored with the same versioned evaluator.

- Score version: `structural_compliance_v1.1`
- Rows: `27000`
- Maximum score drift after re-scoring: `0.000000500`

## Candidate Summary

| candidate | n | composite | style compliance | non-style structural |
| --- | ---: | ---: | ---: | ---: |
| amt_small_controlled | 9000 | 0.732610 | 0.809814 | 0.676704 |
| amt_small_raw | 9000 | 0.560968 | 0.563724 | 0.558971 |
| motif_transform_baseline | 9000 | 0.752682 | 0.854195 | 0.679172 |

## Paired Comparisons

| comparison | n | mean difference | bootstrap 95% CI | paired t p |
| --- | ---: | ---: | ---: | ---: |
| controlled_minus_raw | 9000 | 0.171642 | [0.168923, 0.174287] | <1e-6 |
| controlled_minus_motif | 9000 | -0.020072 | [-0.022331, -0.017814] | <1e-6 |
| motif_minus_raw | 9000 | 0.191714 | [0.188850, 0.194556] | <1e-6 |
