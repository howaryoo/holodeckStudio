# Research: Video Quality Improvements (Free-Stack)

**Goal**: Improve watchability of generated videos with zero-cost tools (no GPU, no paid APIs).

## Scene Transitions

FFmpeg `xfade` filter supports: fade, fadeblack, fadewhite, dissolve, pixelize, wipeleft, wiperight, etc.

Usage:
```
ffmpeg -i scene1.mp4 -i scene2.mp4 -filter_complex "xfade=transition=fadeblack:duration=1:offset=5" output.mp4
```

Requires splitting video into segments per scene, then joining with xfade. Can chain multiple xfades for N scenes.

Limitation: `xfade` needs 2 inputs at a time. For N scenes, need cascaded xfade chains.

## Per-Character Animation (SVG)

Current: 1 SVG frame per dialogue line, static.
Improvement: generate N sub-frames per line with small deltas:
- Breathing: tiny head bobbing (y ±2px)
- Torso sway: slight rotation or x oscillation
- Arm gesture: raise/lower arm lines

Stick-figure joints make this feasible — just vary line endpoint coordinates slightly per sub-frame.

## Richer Environments

Current: `scene_background()` draws a rect + floor line.
Improvement: add furniture from story context (desks, consoles, windows, doors) using existing `prop_icon()` family. Parse location descriptions for furnishing keywords.

## Character Silhouette Detail

Current: circle head + line body + line arms + line legs.
Improvement: add hair (small rect/circle atop head), clothing indicators (neckline, shoulder width), height differentiation between characters.

## Subtitles

FFmpeg `drawtext` filter burns text onto frames:
```
ffmpeg -i video.mp4 -vf "drawtext=text='Hello':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:fontsize=24:fontcolor=white:x=(w-text_w)/2:y=h-th-40" output.mp4
```

Subtitles per line at bottom of frame, synced to dialogue timing.

FFmpeg `subtitles` filter (SRT/ASS) is more complex. `drawtext` is simpler for per-line overlay.

## Audio Pitch Per Character

FFmpeg audio filters for voice differentiation:
- `asetrate=44100*0.9,aresample=44100` — lowers pitch (~deeper voice)
- `asetrate=44100*1.1,aresample=44100` — raises pitch (~higher voice)

Apply different pitch shifts per character to make voices distinct.

Timing: pitch-shift each dialogue audio file individually before concat.

## Audio Ducking

When multiple audio layers exist (dialogue + music/SFX), duck music during speech. Not needed for current MVP (no music layer), but useful for future.

Ken Burns zoompan is already applied (T079). No improvement needed there.

## Split-Screen / Multi-Panel

FFmpeg `hstack` / `vstack` filter:
```
ffmpeg -i left.mp4 -i right.mp4 -filter_complex hstack output.mp4
```

Useful for dialogue scenes showing both characters simultaneously. Could alternate between single-speaker-focus and split-screen.

## Feasibility Summary

| Technique | Complexity | Impact | Effort (tasks) |
|-----------|-----------|--------|-----------------|
| Scene xfade transitions | Medium | High | 3 |
| Per-character animation loops | High | Very High | 5 |
| Richer environments | Low | Medium | 1 |
| Character detail | Low-Medium | Medium | 2 |
| Subtitles via drawtext | Low | High | 2 |
| Per-character audio pitch | Low | Medium | 1 |
| Split-screen dialogue | Medium | Medium | 2 |

Start with highest impact per effort: subtitles + xfade + audio pitch → then richer visuals → then animation loops.
