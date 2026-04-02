# Day 07 — KeyboardOscilloscope

Turn your keyboard into a synthesizer. Every key plays a sine wave. Hold multiple keys to build chords and watch the superposition happen live.

## Run
```
D:\BuildOrcas\run.bat KeyboardOscilloscope
```

## Key layout
```
[ Q ][ W ][ E ][ R ][ T ][ Y ][ U ][ I ]   C5 → C6  (high)
[ A ][ S ][ D ][ F ][ G ][ H ][ J ][ K ]   C4 → C5  (middle)
[ Z ][ X ][ C ][ V ][ B ][ N ][ M ]         C3 → B3  (bass)
```

Number row `1–6` maps C4 E4 G4 A4 B4 C5 — instant C major chord on `1+2+3`.

## What you're seeing

The colored lines are individual sine waves — one per held key. The white line is their sum (superposition). When peaks align you get constructive interference and the wave gets taller. When a peak meets a trough they cancel. The white line shape tells you everything about the harmony — octaves look clean and periodic, dissonant intervals look chaotic.

## What's different from the starter

- Per-key phase accumulators — no clicks or pops when pressing/releasing keys mid-chord
- `np.tanh` soft clipping instead of hard clip — sounds warmer at high volumes
- Display always shows 3 cycles per wave regardless of frequency — bass and treble equally readable
- Visual keyboard strip at the bottom lights up in each note's color when held
- 32 mapped keys across 3 octaves vs starter's 14

## Shipped
- [x] Keypress produces audible tone
- [x] Multiple keys produce a chord with no clicks
- [x] Live waveform shows each channel + superposition
- [x] README filled in

## Stack
`sounddevice` `numpy` `pygame`
