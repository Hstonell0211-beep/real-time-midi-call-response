# macOS Demo Setup

This checkout is configured for an Apple Silicon Mac with Logic Pro.
The live interface is locked to the paper's Controlled AMT pipeline. The
non-neural motif baseline is not selectable during performance and is used
only when Controlled AMT returns zero playable notes.

## Start the control surface

Clone with submodules so the Apple AudioUnit SDK is available:

```zsh
git clone --recurse-submodules <repository-url>
```

Then double-click `start_mac_demo.command`, or run:

```zsh
./start_mac_demo.command
```

The launcher starts a detached local service, opens the control surface, and
then exits. No Terminal window needs to remain open. Open Logic's
`MFP: AI Response` MIDI FX window to use the same surface inside Logic.

The web service isolates CoreMIDI access in a helper process. If macOS briefly
rejects a MIDI client, the control surface stays online, shows the diagnostic,
and retries automatically. Use **Refresh MIDI** after reconnecting a device.

## Logic Pro routing

1. Open Logic Pro and keep the two fixed-role software-instrument tracks:
   `MFP MELODY` for the performer's input and AI response, and `MFP DRUMS` for
   the inferred rhythm guide. Keep both tracks record-enabled.
2. Insert **MIDI FX > Audio Units > MFP > AI Response**. Its custom window is the
   MFP performance surface; the Python service remains the background model engine.
3. Select `MFP MELODY` and choose any Logic instrument or plug-in patch. The live
   keyboard input, AI response, and saved Loop Bank phrases all follow that sound.
4. Select `MFP DRUMS` and choose any Logic drum kit patch. The rhythm guide follows
   that kit independently. Loading patches does not change the track's fixed MIDI
   input port/channel assignment; after editing the project, verify both red `R`
   buttons remain enabled.
5. Start MFP Studio and choose `Minilab3 MIDI` as the input. The program sends AI
   responses and Loop Bank phrases to `Logic Pro Virtual In` on MIDI channel 1,
   and sends the inferred rhythm guide to `Python_OUT` on MIDI channel 10.
6. In Logic, keep the receiving instrument track(s) armed/selected as needed. The
   browser keyboard is only a test input; your MiniLab is the live input.

Signal map:

```text
MiniLab 3 -> MFP Studio
Logic Pro Virtual In / channel 1 -> Logic AI instrument
MFP Python_OUT / channel 10      -> Logic drum instrument
```

Use **学习新节奏**, then tap any MiniLab key to demonstrate timing and accents.
After the tap silence, MFP infers BPM and a 16-step pattern, creates a stable Logic
drum MIDI accompaniment, and aligns AI responses to it. Use **下一小节停止** for a
musical exit or **立即停止** for an emergency stop. Learning again replaces the old
rhythm at the next bar boundary.
After an AI response finishes, save it to Loop Bank A/B/C/D as either only the AI
response or the full Call + Response, then start/stop each slot independently.

The IAC Driver must be online in Audio MIDI Setup with ports named `Python_IN`
and `Python_OUT`.

## Expected performance

The local AMT Small checkpoint runs fully offline. For a reliable demonstration,
the engine uses a 1.8-second neural generation budget and completes any remaining
response notes from the captured phrase's musical template. Real MiniLab tests
produced audible responses in about 1.8-1.9 seconds with no MIDI underruns. This
is a turn-based demonstrator, not the paper's RTX 3060 scheduler configuration.

## Local verification

Run the deployment regressions without MIDI hardware:

```zsh
.venv/bin/python -m unittest discover -s code -p 'test_*.py'
```

The final live check still needs to run in a normal macOS Terminal session so
CoreMIDI and the local `127.0.0.1:8000` listener are available.
