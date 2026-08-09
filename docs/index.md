# Real-Time MIDI Call-and-Response Generation

Code, paper, and verified summary outputs for **Real-Time MIDI Call-and-Response Generation Using Autoregressive Transformers**.

[GitHub repository](https://github.com/MickeyWzt/real-time-midi-call-response) | [Paper PDF](../paper/Real_Time_MIDI_Call_and_Response_Generation_Using_Autoregressive_Transformers.pdf) | [Zenodo v1.1.0 DOI](https://doi.org/10.5281/zenodo.21860065) | [Release archive](https://github.com/MickeyWzt/real-time-midi-call-response/releases/tag/v1.1.0)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21860065.svg)](https://doi.org/10.5281/zenodo.21860065)

![System overview](../paper/System_overview.png)

## What This Project Does

The system adapts an offline Anticipatory Music Transformer to live MIDI co-performance. It listens to a human call phrase, detects the phrase endpoint with MIDI-VAD logic, generates an AI response, applies phrase-level control, and schedules MIDI playback with a latency-aware buffer.

## Evidence Included

| Evidence layer | Scale | Main takeaway |
| --- | ---: | --- |
| Direct endpoint replay | 1,100 call-condition rows | Adaptive F1 is `0.712` at two seconds; fixed 800 ms is `0.708`, with 38 versus 68 premature commits. |
| Harmonized Call100 comparison | 27,000 trials | Shared-batch controlled AMT improves raw AMT by `+0.171642`; the motif baseline remains `0.020072` higher. |
| A0-A6 module ablation | 63,000 rows | Composite rises from `0.560968` to `0.732610`; A4 motif fallback activates `0/9000` times. |
| Preload scheduler replay | 18,000 rows | With `150 ms` of pre-commit overlap, mean endpoint-to-first-MIDI latency decreases from `161.303 ms` to `91.721 ms`. |
| Blind listening | 41 retained participants | A4 is not conclusively above raw AMT; the motif baseline is preferred to A6 on eight fixed stimuli. |

The combined evidence supports an engineering adaptation and measurable structural control. It does not establish universal endpoint accuracy, faster intrinsic decoding, or perceptual superiority.

## Included Materials

- realtime MIDI engine and local browser studio
- Call100 dataset manifest and validation scripts
- trial-level structural metrics, exact score specification, and integrity audits
- endpoint, ablation, and scheduler-replay summaries
- privacy-preserving blind-listening aggregate tables and analysis code
- paper PDF and LaTeX source
- static blind-listening interface retained for transparency
- citation and Zenodo metadata

Large model weights, generated MIDI responses, participant-level exports, exclusion identifiers, audio sample libraries, VST plugins, private answer keys, and deployment credentials are excluded.

## Citation

Use the v1.1.0 DOI [10.5281/zenodo.21860065](https://doi.org/10.5281/zenodo.21860065) for exact reproducibility. The all-versions concept DOI is [10.5281/zenodo.20838083](https://doi.org/10.5281/zenodo.20838083).

```bibtex
@software{wang_hu_2026_realtime_midi_call_response,
  author = {Wang, Zitong and Hu, Sitong},
  title = {Real-Time MIDI Call-and-Response Generation Using Autoregressive Transformers},
  year = {2026},
  version = {1.1.0},
  doi = {10.5281/zenodo.21860065},
  url = {https://doi.org/10.5281/zenodo.21860065}
}
```
