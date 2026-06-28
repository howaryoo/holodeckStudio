# Tasks: Sound Effects & Audio Mixing

**Input**: Design documents from `specs/008-sound-effects/`
**Prerequisites**: plan.md, research.md, spec.md
**Branch**: `008-sound-effects`

---

## Format Guide

- **[ ]**: Not started | **[x]**: Complete
- **T###**: Task ID
- **[SYNC]**: Human review required
- **[ASYNC]**: Agent-delegatable
- **[P]**: Can run in parallel with other [P] tasks at same phase level

---

## Phase 1: SFX Library

**Goal**: Download trekcore.com SFX files and build searchable tag index.

- [x] T001 [ASYNC] Download ~100 Voyager-relevant SFX files from trekcore.com:
  - Use `wget` or `curl` to fetch MP3s from `https://www.trekcore.com/audio/{category}/{filename}.mp3`
  - Create directory structure: `sfx_library/{category}/`
  - Priority categories: background, aliensounds (Borg), computer, doors, medical, redalert, transporter, weapons, turbolift, warp, explosions, holodeck, voice, tricorder, communicator
  - Store in `sfx_library/` at project root
  - Verify each file is valid MP3 (check header bytes)

- [x] T002 [ASYNC] Create `src/holodeck/agents/audio/sfx_library.py`:
  - `class SFXRegistry`:
    ```python
    class SFXRegistry:
        def __init__(self, library_path: str = "sfx_library") -> None: ...
        def load_index(self) -> None: ...  # reads index.json
        def search(self, keyword: str) -> list[SFXEntry]: ...  # tag match
        def get_by_tag(self, tag: str) -> list[SFXEntry]: ...
        def get_ambience(self, location: str) -> SFXEntry | None: ...
        def categories(self) -> list[str]: ...
    
    @dataclass
    class SFXEntry:
        path: str
        category: str
        filename: str
        tags: list[str]
        duration: float  # seconds, from ffprobe
        is_loopable: bool
    ```
  - Load `sfx_library/index.json` on init
  - `search()` matches keyword against tags, filename, category (case-insensitive substring)
  - `get_ambience()` — special: match location string (VOY Bridge → background/voy_bridge.mp3)
  - Cache index in memory

- [x] T003 [ASYNC] Generate `sfx_library/index.json`:
  - Script: `python -m holodeck.scripts.build_sfx_index`
  - Walk `sfx_library/`, read MP3 metadata via `ffprobe` for duration
  - Auto-tag: derive tags from directory name + filename (e.g., `voy_bridge` → ["voy", "bridge", "background", "ambience", "starfleet"])
  - Manual tag overrides file: `sfx_library/tag_overrides.yaml`
  - Write `index.json` with entries: path, category, filename, tags, duration, is_loopable

- [x] T004 [ASYNC] Verify all SFX files:
  - `uv run python -c "from sfx_library import SFXRegistry; SFXRegistry().load_index(); print(f'{len(r.entries)} files')"`
  - All MP3 headers valid
  - No zero-length files
  - Index.json parseable and searchable

**Checkpoint**: `SFXRegistry().search("door")` returns list of door sound entries.

---

## Phase 2: SFX Engine
**Goal**: Parse SoundDesignerAgent output, match cues to files, mix with dialogue.

- [x] T005 [SYNC] Create `src/holodeck/agents/audio/sfx_matcher.py`:
  - `class SFXMatcher`:
    ```python
    class SFXMatcher:
        def __init__(self, registry: SFXRegistry) -> None: ...
        
        def parse_sound_design(self, text: str) -> list[SceneCue]:
            """Extract SCENE blocks from SoundDesigner output. Return list of SceneCue."""
        
        def match_cues(self, scene_cues: list[SceneCue]) -> list[MatchedScene]:
            """For each SceneCue, search registry for AMBIENCE, FOLEY, SFX matches.
            Return list of MatchedScene with file paths."""
    
    @dataclass
    class SceneCue:
        scene_number: int
        ambience: str  # raw text description
        foley: str     # raw text description  
        sfx: list[str] # individual SFX descriptions
    
    @dataclass
    class MatchedScene:
        scene_number: int
        ambience_path: str | None
        foley_paths: list[str]
        sfx_paths: list[str]
    ```
  - Parse `SCENE <N>: <Location>` blocks using regex `r"SCENE (\d+):(.+?)(?=SCENE|\Z)"`
  - Within each block, extract `- AMBIENCE:`, `- FOLEY:`, `- SFX:` lines
  - Split SFX line on commas for individual cues
  - For each cue, call `registry.search(keyword)` — take first match
  - If no match, `None` (silent fallback)
  - Ambience matching: strip common words ("background", "quiet", "ambient"), match remaining keywords

- [x] T006 [SYNC] Create `src/holodeck/agents/audio/audio_mixer.py`:
  - `class AudioMixer`:
    ```python
    class AudioMixer:
        def __init__(self, ffmpeg_path: str = "ffmpeg") -> None: ...
        
        def mix_scene(
            self,
            dialogue_path: str,        # per-scene dialogue MP3
            ambience_path: str | None, # looped ambience
            sfx_paths: list[str],      # one-shot SFX
            output_path: str,          # scene_mixed_N.mp3
            scene_duration: float,     # seconds
        ) -> str: ...  # returns output_path
        
        def concat_scenes(
            self,
            scene_paths: list[str],    # ordered scene mixes
            output_path: str,          # full_audio.mp3
        ) -> str: ...
    ```
  - `mix_scene()` builds FFmpeg command:
    ```
    ffmpeg -i dialogue.mp3 -i ambience.mp3 -i sfx1.mp3 -i sfx2.mp3 \
      -filter_complex "[0:a]volume=1.0[d];[1:a]volume=0.25,aloop=loop=-1:size=44100[a];\
      [2:a]volume=0.5[s1];[3:a]volume=0.5[s2];\
      [d][a][s1][s2]amix=inputs=4:duration=first:dropout_transition=0[out]" \
      -map "[out]" -t {scene_duration} -y scene_mixed.mp3
    ```
    - Dialogue: gain 1.0 (reference)
    - Ambience: gain 0.25 (-12dB), loop via `aloop` if shorter than scene
    - SFX: gain 0.5 (-6dB), one-shot at start (or scheduled with `adelay` for timed effects)
    - Handle variable input count (no fixed amix inputs)
    - If ambience None: skip [a] stream, reduce amix inputs
    - If no SFX: skip [s*] streams
    - If no matches at all: copy dialogue alone (no mix)
  - `concat_scenes()`:
    ```
    ffmpeg -i s1.mp3 -i s2.mp3 -filter_complex concat=n=2:v=0:a=1 full_audio.mp3
    ```

- [x] T007 [ASYNC] Ambience loop handling:
  - Duration detection: `ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 file.mp3`
  - If ambience clip shorter than scene: `aloop=loop=-1:size={samples}` to loop seamlessly
  - If ambience longer: `atrim=0:{scene_duration}` to truncate
  - Crossfade between ambience scenes: `acrossfade` filter (duration=2s for smooth transition)

- [x] T008 [ASYNC] Graceful failure modes:
  - No SFX files downloaded (empty SFX library): dialogue-only output, log warning
  - Partial match: use what matched, skip unmatched cues, log per-cue
  - Corrupted MP3: skip file, log warning, continue
  - FFmpeg missing: skip SFX mixing entirely, dialogue-only fallback

**Checkpoint**: SoundDesigner output → parse → match → mix produces scene audio with ambience + SFX over dialogue.

---

## Phase 3: Pipeline Integration
**Goal**: Wire SFX engine into production pipeline as new stage.

- [x] T009 [ASYNC] Pipeline changes:
  - Add `SFX_MIXER` to `Stage` enum in `src/holodeck/pipeline/stages.py` (between VOICE_SYNTHESIS and FRAME_RENDERER)
  - In `runner.py`, add SFX stage handler:
    ```python
    Stage.SFX_MIXER: {
        "agent": sfx_mixer_agent,
        "context_contract": {"sound_design": str},
        "output_keys": ["mixed_audio_path"],
    },
    ```
  - `sfx_mixer_agent.process(context)`:
    1. Read `context["sound_design"]` (from SoundDesignerAgent output)
    2. Read `context["dialogue_audio_urls"]` (from VoiceSynthesisAgent output)
    3. Parse + match via SFXMatcher
    4. Mix per scene via AudioMixer
    5. Concat scenes into `{output_dir}/full_audio.mp3`
    6. Store path in `context["mixed_audio_path"]`
  - Enable/disable via `context["sfx_enabled"]` (default True) — set False with `--no-sfx` flag in CLI

- [x] T010 [ASYNC] VideoAssembler modification:
  - In `assemble()` or `process()`:
    ```python
    mixed_audio = context.get("mixed_audio_path")
    if mixed_audio and os.path.exists(mixed_audio):
        # Use pre-mixed audio instead of dialogue concat
        ffmpeg_cmd = [
            "ffmpeg", "-i", raw_video, "-i", mixed_audio,
            "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
            "-map", "0:v", "-map", "1:a", "-shortest", output_path
        ]
    else:
        # Existing dialogue-only concat path
    ```
  - Preserve all video filters (camera moves, color grading, subtitles) — audio path is independent
  - If mixed_audio shorter than video: `-shortest` truncates to audio duration (audio reference)
  - If mixed_audio longer: `-shortest` truncates to video duration

**Checkpoint**: Pipeline produces video with dialogue + ambience + SFX. `--no-sfx` flag produces dialogue-only (no regression).

---

## Phase 4: Tests
**Goal**: Unit tests for all new components.

- [x] T011 [P] [ASYNC] Create `tests/unit/test_sfx_library.py`:
  - `test_registry_loads_index()` — load created index
  - `test_search_by_keyword()` — "door" returns door entries
  - `test_search_case_insensitive()` — "DOOR" same as "door"
  - `test_search_no_match_returns_empty()` — "xyzzy" → []
  - `test_get_ambience_matches_location()` — "VOY Bridge" → ambience entry
  - `test_empty_library_no_crash()` — empty dir → empty results, no exception

- [x] T012 [P] [ASYNC] Create `tests/unit/test_sfx_matcher.py`:
  - `test_parse_sound_design_blocks()` — extract SCENE blocks from sample text
  - `test_parse_ambience_foley_sfx_lines()` — parse each line type
  - `test_match_cues_finds_files()` — mock registry, verify matching
  - `test_match_cues_partial_no_crash()` — some cues unmatched, verify partial result
  - `test_match_cues_all_unmatched_returns_none()` — no matches → all None
  - `test_parse_empty_text()` — empty string → empty list

- [x] T013 [P] [ASYNC] Create `tests/unit/test_audio_mixer.py`:
  - `test_mix_scene_dialogue_only()` — no ambience/SFX → copies dialogue
  - `test_mix_scene_with_ambience()` — verify `aloop` in FFmpeg command
  - `test_mix_scene_with_sfx()` — verify multiple sfx inputs
  - `test_mix_scene_volume_levels()` — verify `volume=` filter params
  - `test_concat_scenes()` — verify concat filter string
  - `test_mix_scene_missing_ffmpeg()` — FileNotFoundError → warning, return None

- [x] T014 [ASYNC] Integration test — `tests/integration/test_sfx_pipeline.py`:
  - Full pipeline with mock SoundDesigner output
  - Verify `context["mixed_audio_path"]` created
  - Verify output file valid MP3
  - Verify `--no-sfx` flag skips SFX stage

**Checkpoint**: All new tests pass alongside existing 305.

---

## Phase 5: Verification
- [x] T015 [ASYNC] Run lint + type check:
  - `uv run ruff check src/holodeck/agents/audio/sfx_*.py` — 0 new errors
  - `uv run mypy src/holodeck/agents/audio/sfx_*.py tests/unit/test_sfx_*.py` — 0 errors
  - `uv run pytest tests/unit/ -x` — 305 + N new pass

---

## Task Dependency Graph

```
Phase 1
T001 (DOWNLOAD) → T002 (SFXRegistry) → T003 (INDEX) → T004 (VERIFY)
                                                              ↓
Phase 2
T005 (SFXMatcher) → T006 (AudioMixer) → T007 (AMB LOOP) → T008 (FALLBACK)
                                                              ↓
Phase 3
T009 (PIPELINE) → T010 (VIDEO ASSEMBLER)
                         ↓
Phase 4                    Phase 5
T011 ─────┐               T015
T012 ─────┤ (parallel)
T013 ─────┤
T014 ─────┘
```

**Critical path**: T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T015

---

## Definition of Done

- [x] `uv run pytest tests/unit/ -x` — all pass (305 + N new)
- [x] `uv run ruff check src/holodeck/agents/audio/sfx_*.py` — 0 new errors
- [x] `uv run mypy src/holodeck/agents/audio/sfx_*.py tests/unit/test_sfx_*.py` — 0 errors
- [ ] `holodeck produce "story"` produces video with ambience + SFX (no more silence between dialogue)
- [ ] `holodeck produce "story" --no-sfx` produces dialogue-only video (no regression)
- [ ] Empty SFX library produces dialogue-only output with warning log
