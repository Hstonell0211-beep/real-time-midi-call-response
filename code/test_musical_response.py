import threading
import unittest

from live_call_response import (
    CapturedNote,
    LiveCallResponseApp,
    MusicalResponseController,
    PhraseRecorder,
    ResponsePlan,
    GeneratedEvent,
    analyze_call_phrase,
    apply_live_pentatonic_style,
    build_rescue_response_events,
    build_response_plan,
    should_capture_rhythm_pad,
    should_use_motif_fallback,
)
from midi_vad_endpoint import EndpointDecision, MidiNoteEvent


class MusicalResponseTests(unittest.TestCase):
    def test_motif_fallback_is_only_for_empty_controlled_amt_output(self):
        allowed = should_use_motif_fallback(
            generated_count=0,
            fallback_on_empty=True,
            backend="amt",
            response_strategy="controlled_amt",
            stopped=False,
        )

        self.assertTrue(allowed)
        for override in (
            {"generated_count": 1},
            {"fallback_on_empty": False},
            {"backend": "aria"},
            {"response_strategy": "motif"},
            {"stopped": True},
        ):
            inputs = {
                "generated_count": 0,
                "fallback_on_empty": True,
                "backend": "amt",
                "response_strategy": "controlled_amt",
                "stopped": False,
            }
            inputs.update(override)
            self.assertFalse(should_use_motif_fallback(**inputs))

    def test_phrase_scale_prefers_played_collection(self):
        notes = [
            CapturedNote(index * 0.25, pitch, 90, duration=0.18)
            for index, pitch in enumerate((60, 62, 64, 67, 69, 72))
        ]

        profile = analyze_call_phrase(notes)

        self.assertEqual(profile.scale_root, 0)
        self.assertEqual(profile.scale_mode, "major")

    def test_empty_model_fallback_uses_published_tail_inversion(self):
        notes = [
            CapturedNote(index * 0.25, pitch, 92, duration=0.16)
            for index, pitch in enumerate((60, 62, 64, 65))
        ]
        profile = analyze_call_phrase(notes)
        plan = ResponsePlan(2.0, 4, 48, 84, 2, 0.35, 8)

        events = build_rescue_response_events(notes, profile, plan, None, 0.25, 0.04, 2.5)

        self.assertEqual(len(events), 4)
        center = round(profile.mean_pitch)
        self.assertEqual(
            [event.pitch for event in events],
            [center - (note.pitch - center) + 5 for note in notes],
        )
        self.assertEqual(events[0].tick, 0)
        self.assertTrue(all(later.tick > earlier.tick for earlier, later in zip(events, events[1:])))

    def test_controller_preserves_chromatic_model_output_within_register(self):
        notes = [CapturedNote(0.0, 60, 90, duration=0.2), CapturedNote(0.3, 64, 90, duration=0.2)]
        profile = analyze_call_phrase(notes)
        plan = ResponsePlan(2.0, 4, 55, 72, 2, 0.35, 8)
        controller = MusicalResponseController(profile, plan)
        first = controller.accept(GeneratedEvent(0, 20, 60, 0, 120))
        chromatic = controller.accept(GeneratedEvent(25, 20, 61, 0, 127))
        clipped = controller.accept(GeneratedEvent(50, 20, 90, 0, 127))

        self.assertEqual(first.pitch, 60)
        self.assertEqual(chromatic.pitch, 61)
        self.assertEqual(clipped.pitch, 72)
        self.assertEqual(chromatic.velocity, 127)

    def test_controller_rejects_excessive_same_pitch_run(self):
        notes = [CapturedNote(0.0, 60, 90, duration=0.2)]
        profile = analyze_call_phrase(notes)
        plan = ResponsePlan(2.0, 4, 48, 72, 2, 0.35, 8)
        controller = MusicalResponseController(profile, plan)
        controller.accept(GeneratedEvent(0, 20, 60, 0, 90))
        controller.accept(GeneratedEvent(25, 20, 60, 0, 90))

        self.assertEqual(
            controller.rejection_reason(GeneratedEvent(50, 20, 60, 0, 90)),
            "repeat",
        )

    def test_live_paper_style_projects_scale_limits_leaps_and_adds_cadence(self):
        notes = [
            CapturedNote(index * 0.2, pitch, 90, duration=0.12)
            for index, pitch in enumerate((60, 62, 64, 67, 69, 67, 64, 62, 60))
        ]
        profile = analyze_call_phrase(notes)
        plan = ResponsePlan(2.0, 6, 48, 81, 2, 0.35, 8)
        raw = [
            GeneratedEvent(index * 25, 20, pitch, 0, 90)
            for index, pitch in enumerate((61, 66, 65, 65, 71, 63))
        ]

        styled = apply_live_pentatonic_style(raw, profile, plan)

        allowed = {0, 2, 4, 7, 9}
        self.assertTrue(all(event.pitch % 12 in allowed for event in styled))
        self.assertTrue(all(abs(b.pitch - a.pitch) <= 7 for a, b in zip(styled, styled[1:])))
        self.assertTrue(all(a.pitch != b.pitch for a, b in zip(styled, styled[1:])))
        self.assertEqual(styled[-1].pitch % 12, 0)

    def test_short_call_can_receive_a_compact_response(self):
        profile = analyze_call_phrase([CapturedNote(0.0, 60, 92, duration=0.12)])
        plan = build_response_plan(
            profile=profile,
            response_seconds=3.0,
            max_events=12,
            pitch_min=36,
            pitch_max=96,
            response_length_ratio=1.0,
            response_note_ratio=1.0,
            same_pitch_limit=2,
            dominant_pitch_max_share=0.35,
            resample_attempts=8,
        )

        self.assertEqual(plan.target_seconds, 0.85)

    def test_rhythm_learning_only_captures_the_dedicated_pad_lane(self):
        class MidiMessage:
            def __init__(self, note, channel):
                self.type = "note_on"
                self.note = note
                self.channel = channel

        self.assertFalse(should_capture_rhythm_pad(MidiMessage(60, 0), True, 36, 51, 9))
        self.assertTrue(should_capture_rhythm_pad(MidiMessage(36, 9), True, 36, 51, 9))
        self.assertFalse(should_capture_rhythm_pad(MidiMessage(36, 9), False, 36, 51, 9))

    def test_phrase_completed_during_ai_playback_is_queued_then_handed_off(self):
        # Build only the small live-state surface needed for this concurrency
        # test; loading an AMT model is irrelevant here.
        app = LiveCallResponseApp.__new__(LiveCallResponseApp)
        app.recorder = PhraseRecorder(default_duration=0.1)
        app.busy = threading.Event()
        app.busy.set()
        app.pending_lock = threading.Lock()
        app.pending_response = None
        app.round_id = 0
        app.round_lock = threading.Lock()

        app.recorder.note_on(64, 92, 0, 10.0)
        app.recorder.note_off(64, 0, 10.2)
        decision = EndpointDecision(
            phrase=[MidiNoteEvent(timestamp=10.0, pitch=64, velocity=92)],
            cut_time=10.3,
            last_event_time=10.0,
            silence=0.3,
            mu_tempo=2.0,
            tau_cutoff=0.3,
            survival=0.05,
            theta=0.05,
        )

        app.on_endpoint(decision)

        self.assertIsNotNone(app.pending_response)
        queued_phrase, queued_decision = app.pending_response
        self.assertEqual([note.pitch for note in queued_phrase], [64])
        self.assertIs(queued_decision, decision)

        started = []
        app._start_response_cycle = lambda phrase, endpoint, preload=None, **kwargs: started.append(
            (phrase, endpoint, preload, kwargs)
        )
        app._start_pending_response_or_mark_idle()

        self.assertEqual(len(started), 1)
        self.assertEqual([note.pitch for note in started[0][0]], [64])
        self.assertTrue(started[0][3]["queued"])
        self.assertTrue(app.busy.is_set())
        self.assertIsNone(app.pending_response)


if __name__ == "__main__":
    unittest.main()
