# v1.1.0

Integrity and evidence-chain release for **Real-Time MIDI Call-and-Response Generation Using Autoregressive Transformers**.

Zenodo version DOI: https://doi.org/10.5281/zenodo.21860065
All-versions concept DOI: https://doi.org/10.5281/zenodo.20838083

## Corrections

- Corrects the v1.0.0 candidate condition labeled `amt_small_raw`. That path had applied style projection and was not comparable with ablation A0.
- Replaces the old candidate claim (`0.683141` raw and `+0.063907` controlled-minus-raw) with a harmonized shared-batch evaluation: raw `0.560968`, controlled `0.732610`, motif `0.752682`, and controlled-minus-raw `+0.171642` with 95% CI `[0.168923, 0.174287]`.
- Separates event-level repair from phrase-level motif fallback. A4 motif fallback activated `0/9000` times because A3 produced no empty outputs; all A3/A4 MIDI pairs are byte-identical.
- Defines the versioned structural-compliance score, all six component formulas, weights, normalizations, and style/non-style decomposition.
- Uses `p<10^-6` when floating-point p-values underflow instead of reporting `p=0`.
- Aligns the speculative-preload overlap with the endpoint confirmation interval at `150 ms`; no `250 ms` post-confirmation horizon is claimed.

## New Evidence

- 27,000-row harmonized candidate-level trial metrics with hashes and path-redacted provenance.
- Direct 100-call endpoint benchmark with adaptive, fixed 300/500/800 ms, clustering, and confirmation-window conditions.
- Fallback activation, A3/A4 paired identity, score decomposition, and legacy-label integrity audits.
- Privacy-preserving blind-listening aggregate outputs for 44 complete submissions and 41 retained participants, plus the frozen analysis script and source hashes.
- Revised manuscript with seven figures, a claim/evidence hierarchy, explicit limitations, hardware environment, and corrected terminology.

## Claim Boundary

The release supports an external engineering adaptation, measurable structural control, and scheduler-level responsiveness. It does not establish universal endpoint accuracy, faster intrinsic AMT decoding, or perceptual superiority.

## Excluded

- model weights and third-party audio software
- generated MIDI response batches and license-sensitive source datasets
- participant-level response exports and exclusion identifiers
- private blind-study answer keys and deployment credentials
