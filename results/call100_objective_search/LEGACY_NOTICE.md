# Legacy v1.0.0 Candidate Evaluation

This directory is retained to make the original release auditable. Its condition labeled
`amt_small_raw` passed the generated AMT response through style projection and therefore
was not equivalent to the true raw A0 configuration. The resulting mean `0.683141` and
controlled-minus-raw difference `+0.063907` are superseded.

Use `../call100_harmonized_evaluation/` for manuscript claims. That evaluation reuses true
A0 raw and A6 controlled outputs from one seeded ablation batch, re-scores all three
candidates with `structural_compliance_v1.1`, and reports raw `0.560968`, controlled
`0.732610`, and motif baseline `0.752682`.

The legacy CSVs are preserved byte-for-byte from v1.0.0 and therefore retain historical
machine-local path strings. Those generated MIDI files are not part of the public archive.
