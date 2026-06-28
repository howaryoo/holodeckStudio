# Research: Sound Effects & Audio Mixing

## SFX Source: trekcore.com

**URL**: https://www.trekcore.com/audio/
**License**: Fan site hosting Star Trek clips. Experimental/personal use. Not for redistribution.
**Format**: Direct MP3 downloads via `https://www.trekcore.com/audio/{category}/{filename}.mp3`

### Categories Available

| Category | Content | Voyager Relevance |
|----------|---------|-------------------|
| `aliensounds/` | Borg (adapt, beam, cutting beam, engine, phaser, transporter, stepping), Cardassian, Klingon, Romulan | HIGH - Borg sounds for Seven's backstory |
| `background/` | VOY Bridge, Engineering, Astrometrics, Warp Core | HIGH - Scene ambience |
| `brig/` | Forcefield on/off/disable/hit | MEDIUM |
| `cloaking/` | Klingon/Romulan cloak/decloak | LOW |
| `communicator/` | TNG chirps, TOS chirps, ENT communicator | LOW |
| `computer/` | Alarms (1-26), alerts (1-26), computer beeps (1-77), console warning, damage alarm, deny beep, hailing frequencies, keypress (1-6), processing | HIGH - Background computer sounds |
| `doors/` | VOY Door Chime 1/2, TNG doors, DS9 doors, TOS swoosh | HIGH - Scene transitions |
| `explosions/` | Console explode (1-3), large explosion (1-4), small explosion (1-3), shield impact sizzle | MEDIUM |
| `holodeck/` | Holodeck end program, holoemitter, hologram on/off, hologrid online/failing | MEDIUM |
| `medical/` | Hypospray (1-3), laser scalpel, medical scanner, TOS sickbay sounds | HIGH - The Doctor scenes |
| `misc/` | Power up/down, probe launch, Q's flash, runabout flyby, ship shutdown, tractor beam | MEDIUM |
| `redalert/` | VOY Red Alert (1-2), VOY Blue Alert (landing), VOY Intruder Alert, TNG red alert, DS9 red alert, TOS red alert | HIGH - Action scenes |
| `replicator/` | DS9 replicator, TNG replicator, VOY sickbay replicator | MEDIUM |
| `transporter/` | VOY Transporter (1-2), VOY Unstable Transporter, TNG transporter (1-11), TOS transporter (1-16) | HIGH - Character arrivals |
| `tricorder/` | TNG tricorder (1-12), DS9 tricorder (1-3), TOS tricorder | MEDIUM |
| `turbolift/` | VOY Turbolift, DS9 turbolift, TNG turbolift | MEDIUM |
| `viewscreen/` | TNG viewscreen on/off, TOS main viewing screen | LOW |
| `warp/` | TNG warp (1-7, slow, exit, flash, out), TOS warp flyby, TMP warp | MEDIUM |
| `weapons/` | TNG phaser (1-11), TNG torpedo (1-3), TNG disruptor, TOS phaser (1-9), photon torpedo (1-2), quantum torpedo | MEDIUM |
| `voice/` | Computer voice: "Red Alert", "Auto Destruct", "Intruder Alert", "Unable to Comply", etc. | MEDIUM |
| `toscomputer/` | TOS computer beeps, sequences | LOW |

### Download Scope (~100 files target)

Prioritize Voyager-specific + generic usable sounds:
- `background/`: voy_bridge, voy_engineering, voy_astrometrics, voy_warp_core_1-4, tng_bridge_1-3, tng_sickbay_1-2, tng_engine_1-3
- `aliensounds/`: borg_adapt_1-4, borg_beam, borg_cutting_beam_1-3, borg_engine_hum, borg_phaser, borg_transporter_1-2, borg_stepping
- `computer/`: alarm_1-3, alert_1-6, computer_beep_1-20 (subset), console_warning, damage_alarm, hail_alert_1-2, hailing_frequencies_open_1-4, keypress_1-6
- `doors/`: voy_door_chime_1-2, tng_door_open, tng_door_close, tng_doors_1-2
- `medical/`: hypospray_1-3, laser_scalpel, medical_scanner_bay
- `redalert/`: voy_red_alert, voy_red_alert_2, voy_intruder_alert, voy_blue_alert
- `transporter/`: voy_transporter_1-2, voy_unstable_transporter
- `replicator/`: voy_sickbay_replicator
- `turbolift/`: voy_turbolift
- `weapons/`: borg_phaser, tng_phaser_1-5, tng_torpedo_1-3
- `warp/`: tng_warp_1-3
- `explosions/`: console_explode_1-3, large_explosion_1-2, small_explosion_1-2
- `holodeck/`: holodeck_end_program, hologram_on, hologram_off_1-2, hologrid_online
- `voice/`: subset of useful voice announcements
- `tricorder/`: tng_tricorder_1-5
- `communicator/`: tng_chirp_1-3

## Integration Approach

### Current Pipeline Audio Flow
```
ComposerAgent (text score) → SoundDesignerAgent (text SFX design)
→ VoiceDirectorAgent → VoiceSynthesisAgent (dialogue MP3s)
→ FrameRendererAgent → VideoAssemblerAgent (dialogue only FFmpeg concat)
```

### Target Audio Flow
```
SoundDesignerAgent output → SFXMatcher → matched SFX files per scene
                                                     ↓
ComposerAgent output → MusicSelector → matched BGM per scene (DEFERRED)
                                                     ↓
VoiceSynthesisAgent (dialogue MP3s) ─┐
SFXMatcher (matched SFX WAVs) ───────→ AudioMixer (FFmpeg amix)
MusicSelector (BGM tracks) ─────────┘     ↓
                                     Mixed audio track
                                          ↓
VideoAssemblerAgent (video + mixed audio)
```

### SFX Matching Strategy

SoundDesignerAgent output format:
```
SCENE 1: Sickbay
- AMBIENCE: medical bay hum, quiet beeping
- FOLEY: footsteps on deck plates, hypospray application
- SFX: door hiss, tricorder scan, regenerator pulse
```

Extraction: regex `SCENE <N>` blocks, parse `AMBIENCE/FOLEY/SFX:` lines.
Matching: keyword extraction (TF-IDF or simple word → tag mapping) → file lookup.

### FFmpeg Mixing Strategy

```
# Per scene mix:
ffmpeg -i dialogue.mp3 -i ambience.mp3 -i sfx_a.mp3 -i sfx_b.mp3 \
  -filter_complex "[0:a]volume=1.0[d];[1:a]volume=0.3[a];[2:a]volume=0.5[s1];[3:a]volume=0.6[s2];\
  [d][a][s1][s2]amix=inputs=4:duration=first:dropout_transition=0[out]" \
  -map "[out]" scene_mixed.mp3

# Concatenate scene mixes:
ffmpeg -i scene1.mp3 -i scene2.mp3 -filter_complex concat=n=2:v=0:a=1 full_audio.mp3
```

Volume levels:
- Dialogue: 0dB (reference)
- Ambience: -12dB to -18dB (0.15-0.25 gain)
- SFX: -6dB to -12dB (0.25-0.50 gain)
- Music: -20dB (0.10 gain) — deferred

## Existing Code Reuse

- `src/holodeck/agents/video/ffmpeg_utils.py`: Has `build_concat_filter()`, `build_audio_mix_filter()` — extend for multi-source amix
- `src/holodeck/agents/video/video_assembler.py`: `_concat_audio_with_video()` around line 441 — extend to accept mixed audio track
- `src/holodeck/pipeline/runner.py`: Stage enum + run() — add new stage before video_assembler

## Risks

| Risk | Mitigation |
|------|------------|
| trekcore.com goes down | Bundle ~100 core SFX files locally; document source URL |
| SFX matching misses | Broad keyword→tag mapping; fallback to silence per scene |
| Audio sync drifts | Per-scene mixing + concat; dialogue always reference |
| Copyright uncertainty | Experimental/personal use only; user responsibility |
