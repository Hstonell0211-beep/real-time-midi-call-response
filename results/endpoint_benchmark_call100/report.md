# Call100 MIDI-VAD Endpoint Benchmark

Reference boundary: final Note-Off in each isolated Call100 MIDI file.
A commit earlier than 100 ms before the reference is premature. Results are
reported at 0.5, 1.0, and 2.0 s post-boundary deadlines; the table below uses 2.0 s.
This file-end proxy is reproducible but is not a substitute for human boundary annotation.

| condition | precision | recall | F1 [95% CI] | median error (s) | MAE (s) | cancel rate | premature commits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| adaptive_full | 0.624 | 0.830 | 0.712 [0.638, 0.784] | 0.796 | 0.860 | 0.070 | 38 |
| adaptive_no_clustering | 0.610 | 0.830 | 0.703 [0.623, 0.777] | 0.796 | 0.844 | 0.087 | 42 |
| adaptive_no_confirmation | 0.597 | 0.860 | 0.705 [0.633, 0.770] | 0.632 | 0.735 | 0.000 | 49 |
| adaptive_neither | 0.571 | 0.840 | 0.680 [0.606, 0.750] | 0.632 | 0.715 | 0.000 | 53 |
| fixed_300ms | 0.250 | 0.760 | 0.376 [0.319, 0.434] | 0.330 | 0.301 | 0.374 | 228 |
| fixed_500ms | 0.427 | 0.880 | 0.575 [0.517, 0.636] | 0.500 | 0.436 | 0.116 | 118 |
| fixed_800ms | 0.575 | 0.920 | 0.708 [0.646, 0.767] | 0.793 | 0.703 | 0.130 | 68 |
| cluster_40ms | 0.622 | 0.840 | 0.715 [0.642, 0.786] | 0.795 | 0.843 | 0.069 | 40 |
| cluster_120ms | 0.617 | 0.820 | 0.704 [0.628, 0.777] | 0.795 | 0.858 | 0.063 | 38 |
| confirm_75ms | 0.597 | 0.830 | 0.695 [0.620, 0.767] | 0.705 | 0.792 | 0.028 | 44 |
| confirm_250ms | 0.648 | 0.830 | 0.728 [0.650, 0.800] | 0.896 | 0.953 | 0.117 | 33 |
