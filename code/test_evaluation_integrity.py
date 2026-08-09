from __future__ import annotations

import inspect
import importlib.util
import random
import tempfile
import unittest
from pathlib import Path

import evaluate_melody_metrics as evaluator
import offline_ab_test as offline


class EvaluationIntegrityTests(unittest.TestCase):
    def test_weights_and_decomposition_are_exact(self) -> None:
        self.assertAlmostEqual(sum(evaluator.OBJECTIVE_WEIGHTS.values()), 1.0)
        self.assertAlmostEqual(
            evaluator.STYLE_COMPLIANCE_WEIGHT + evaluator.NON_STYLE_STRUCTURAL_WEIGHT,
            1.0,
        )

    def test_empty_output_scores_zero(self) -> None:
        args = evaluator.build_parser().parse_args([])
        result = evaluator.evaluate_notes([], 480, args)
        self.assertEqual(result["objective_score"], 0.0)
        self.assertEqual(result["style_compliance_score"], 0.0)
        self.assertEqual(result["non_style_structural_score"], 0.0)

    def test_raw_amt_has_no_style_projection(self) -> None:
        source = inspect.getsource(offline.generate_raw_amt)
        self.assertNotIn("apply_response_style", source)

    def test_a4_is_the_only_new_motif_fallback_switch_after_a3(self) -> None:
        a3 = offline.ablation_modules("A3_duration_matching")
        a4 = offline.ablation_modules("A4_fallback")
        changed = {key for key in a3 if a3[key] != a4[key]}
        self.assertEqual(changed, {"fallback"})
        self.assertFalse(a3["fallback"])
        self.assertTrue(a4["fallback"])

    @unittest.skipUnless(importlib.util.find_spec("anticipation"), "optional anticipation runtime is unavailable")
    def test_motif_fallback_generator_produces_playable_midi(self) -> None:
        args = offline.build_parser().parse_args(["--input-midi", "synthetic_call.mid"])
        notes = [
            offline.CapturedNote(
                onset=index * 0.4,
                pitch=pitch,
                velocity=90,
                duration=0.3,
            )
            for index, pitch in enumerate([60, 62, 64, 67, 69, 67, 64, 62])
        ]
        profile = offline.analyze_call_phrase(notes)
        response_seconds = offline.response_seconds_for(profile, args)
        _, response, _ = offline.generate_motif_baseline(notes, response_seconds, args, random.Random(20260809))
        self.assertGreater(len(response), 0)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fallback.mid"
            offline.save_events_as_midi(offline.shift_events_to_zero(response), path, args)
            scored_notes, ticks_per_beat = evaluator.read_notes(path)
            scored = evaluator.evaluate_notes(scored_notes, ticks_per_beat, evaluator.build_parser().parse_args([]))
            self.assertGreater(scored["note_count"], 0)
            self.assertGreater(scored["objective_score"], 0)


if __name__ == "__main__":
    unittest.main()
