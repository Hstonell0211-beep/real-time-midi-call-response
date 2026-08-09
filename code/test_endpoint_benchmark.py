from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from midi_vad_endpoint import MidiEndpointVAD
from run_endpoint_benchmark import FixedCutoffVAD, metric_bundle


class EndpointBenchmarkTests(unittest.TestCase):
    def test_confirmation_cancels_internal_pause_candidate(self) -> None:
        candidates = []
        cancels = []
        decisions = []
        detector = FixedCutoffVAD(
            0.3,
            endpoint_confirm_delay=0.15,
            on_candidate_endpoint=candidates.append,
            on_candidate_cancel=cancels.append,
            on_endpoint=decisions.append,
        )
        detector.observe_note_on(60, timestamp=0.0)
        detector.tick(0.31)
        detector.observe_note_on(62, timestamp=0.40)
        detector.tick(0.71)
        detector.tick(0.86)
        self.assertEqual(len(candidates), 2)
        self.assertEqual(len(cancels), 1)
        self.assertEqual(len(decisions), 1)

    def test_no_confirmation_commits_during_same_pause(self) -> None:
        decisions = []
        detector = FixedCutoffVAD(
            0.3, endpoint_confirm_delay=0.0, on_endpoint=decisions.append
        )
        detector.observe_note_on(60, timestamp=0.0)
        detector.tick(0.31)
        detector.observe_note_on(62, timestamp=0.40)
        self.assertEqual(len(decisions), 1)

    def test_metric_bundle_counts_extra_decision_as_false_positive(self) -> None:
        rows = [
            {
                "matched_2000ms": 1,
                "false_positive_count_2000ms": 1,
                "false_negative_count_2000ms": 0,
                "endpoint_error_s_2000ms": 0.4,
            },
            {
                "matched_2000ms": 1,
                "false_positive_count_2000ms": 0,
                "false_negative_count_2000ms": 0,
                "endpoint_error_s_2000ms": 0.5,
            },
        ]
        metrics = metric_bundle(rows, 2.0)
        self.assertAlmostEqual(metrics["precision"], 2 / 3)
        self.assertAlmostEqual(metrics["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
