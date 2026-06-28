# Data Model: Video Quality Improvements

## New Data Entities

### SubtitleData

Per-dialogue-line subtitle info passed from FrameRendererAgent → VideoAssemblerAgent via context.

```
SubtitleData {
  frame_index: int           // Position in frame sequence (0-based)
  dialogue_text: str         // The spoken line text (no speaker prefix)
  character: str             // Speaking character name
  scene: str                 // Scene number/location identifier
  audio_file: str            // Path to corresponding .mp3 (set by VoiceSynthesis)
  audio_duration_sec: float  // Duration of this dialogue line's audio
  start_offset_sec: float    // Cumulative start time in final audio timeline
  end_offset_sec: float      // Cumulative end time in final audio timeline
}
```

**Storage**: In-memory via `context["subtitle_data"]`. Not persisted to cache.

### PitchConfig

Per-character audio pitch shift parameters.

```
PitchConfig {
  character: str             // Character name (uppercase)
  semitones: float           // Pitch shift in semitones (-5 to +5)
  // Male default: -2, Female default: +3, Neutral: 0
}
```

**Storage**: Hardcoded map in `ffmpeg_utils.py`. Overridable via context.

### SceneSegment

A contiguous group of frames belonging to one scene, used for xfade transitions.

```
SceneSegment {
  index: int                 // Segment position (0-based)
  scene: str                 // Scene number/location
  frame_indices: list[int]  // Indices of frames in this segment
  video_file: str           // Temp path to rendered .mp4 for this segment
  duration_sec: float       // Total duration of this segment
}
```

**Storage**: Temp files during VideoAssemblerAgent.process(). Not persisted.

### AnimationSubFrame

One of N sub-frames that make up a per-dialogue-line animation sequence.

```
AnimationSubFrame {
  dialogue_line_index: int  // Which dialogue line this belongs to
  sub_index: int            // 0 to N-1 within the dialogue line
  svg_content: str          // Full SVG string for this sub-frame
  pose_delta: dict          // {"head_y": 2, "arm_angle": 5} relative to neutral
}
```

**Storage**: In-memory within FrameRendererAgent. Output as `---NEXT FRAME---` delimited SVGs.

## Modified Context Keys

| Key | Type | Description | Set By |
|-----|------|-------------|--------|
| `subtitle_data` | `list[SubtitleData]` | Per-line subtitle info with timing | FrameRendererAgent (T088) |
| `pitch_config` | `dict[str, float]` | Character → semitones map | VoiceSynthesisAgent or default (T087) |
| `scene_segments` | `list[SceneSegment]` | Scene grouping metadata | VideoAssemblerAgent (T090) |

## Modified Agent Metadata (AgentOutput.metadata)

### FrameRendererAgent

| Field | Type | Description |
|-------|------|-------------|
| `subtitle_data` | `list[dict]` | Serialized SubtitleData list |
| `animation_subframes` | `int` | Number of sub-frames per dialogue line (if > 1) |

### VideoAssemblerAgent

| Field | Type | Description |
|-------|------|-------------|
| `xfade_applied` | `bool` | Whether xfade transitions were used |
| `subtitles_burned` | `bool` | Whether drawtext subtitles were applied |
| `scene_segments` | `int` | Number of scene segments processed |
