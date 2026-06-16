# Research: Video Enhancement (Free-Stack)

**Goal**: Transform generated video quality from stick-figure demo to watchable short film.

## SVG Character Art — Beyond Stick Figures

Current: 11-node stick figure (head circle + spine + 4 limbs + 2 feet + 2 hands).

Enhancement: Multi-layer SVG character with:
- **Head**: ellipse with facial features (eyes, nose, mouth line). Mouth switches between 2 states (closed/open) for lip-sync.
- **Hair**: SVG path or grouped circles atop head. Styles (short, long, bald, ponytail) parameterized.
- **Torso**: filled polygon with neckline, shoulders, waist. Clothing indicators (collar, uniform line).
- **Arms**: upper arm + forearm with joints, ending in hand shape (not just lines).
- **Legs**: thigh + calf with feet (shoes/boots).
- **Accessories**: hat, cape, belt, weapon, badge — SVG paths conditionally added.

SVG compositing keeps everything B&W-compatible and deterministic — no image generation needed.

## Smooth Camera Motion

Current: `zoompan` per-input-frame with `d=N` → zoom resets on each new frame → jarring.

Better approach:
1. Render all scene frames as a single video segment (concat all scene PNGs)
2. Apply zoompan ONCE over the entire concatenated video → smooth continuous zoom
3. No per-frame reset because zoompan sees one continuous input stream

Or: use `scale` filter with `setpts` expression for smooth zoom:
```
scale=iw*zoom_factor:ih*zoom_factor,setpts=PTS
```
Combined with `crop` for pan:
```
crop=iw/zoom_factor:ih/zoom_factor:(iw/iw)*pan_x:(ih/ih)*pan_y
```

Can chain: `crop` (pan) → `scale` (zoom) → `setsar` (fix aspect).

## Piper TTS — Local Neural TTS

gTTS (current): cloud-based, robotic, 1 voice only, no control over pace/emotion.

Piper TTS: local inference on CPU, ~50MB model, multiple voices (US male, US female, UK male, etc.), runs without GPU, MIT license.

Install: `pip install piper-tts` (or download binary).
Usage:
```
echo "Hello world" | piper --model en_US-lessac-medium --output_file hello.wav
```

Pipeline integration: replace gTTS in VoiceSynthesisAgent with piper. Map character gender to piper voice models. Fall back to gTTS if piper not installed.

Limitation: piper generates .wav (not .mp3). Need FFmpeg to convert to .mp3 before pipeline concat.

Models (all free, ~50MB each):
- `en_US-lessac-medium` — US female
- `en_US-amy-medium` — US female (alternative)
- `en_US-libritts_r-medium` — US male
- `en_GB-alan-medium` — UK male
- `en_GB-semaine-medium` — UK female

## Color Grading with FFmpeg

Current: `colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0` — fixed B&W.

Better: Use per-scene color grading:
- **Sepia**: `colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0`
- **Cool tone**: `colorbalance=rs=-.1:gs=-.1:bs=.2`
- **Warm tone**: `colorbalance=rs=.15:gs=.05:bs=-.1`
- **Film noir**: `colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0` + `curves=vintage`
- **Desaturated with tint**: `hue=s=0` + `colorbalance`

Can also apply `curves` filter for contrast/tonal adjustments:
```
curves=all='0/0 0.25/0.15 0.75/0.85 1/1'
```

## Multi-Character Framing

Two approaches for multi-character frames:

**A. Side-by-side with hstack**:
```
ffmpeg -i left_char.mp4 -i right_char.mp4 -filter_complex \
  "[0:v]crop=iw/2:ih:0:0[left];[1:v]crop=iw/2:ih:iw/2:0[right];[left][right]hstack"
```
Limitation: needs separate video streams per character.

**B. Composite SVG frame**:
Generate a single SVG with both characters positioned in the frame. Active speaker at (x=320, y=360) scaled 1.0x, listener at (x=100, y=380) scaled 0.7x. This is simpler and keeps the single-PNG-per-frame model.

Approach B is preferred — modify FrameRendererAgent to accept `characters_in_scene` parameter and render multiple silhouettes per frame.

## Layered Backgrounds

Current: single rect + floor line + optional props.

Better: 3-layer background per scene:
1. **Background**: sky/ceiling gradient + distant elements (mountains, stars, buildings)
2. **Midground**: room walls, furniture, structural elements
3. **Foreground**: nearby objects, frame edges, vignette

Each layer is an SVG group. Composited in order: background → midground → characters → foreground.

Depth effect: foreground elements larger, background smaller, midground at normal scale.

## Lip Sync (Approximation)

No GPU means no real lip-sync AI. Alternative: time mouth animation to audio amplitude.

Approach: analyze dialogue audio volume envelope with FFmpeg `volumedetect` or `ebur128`. When amplitude > threshold → open mouth (second SVG mouth shape). When quiet → closed mouth.

Or simpler: for each dialogue line, alternate mouth shapes at speech cadence (every 4-6 frames) during the line's sub-frames. This gives illusion of talking without any audio analysis.

## Feasibility Summary

| Technique | Complexity | Impact | Effort (tasks) |
|-----------|-----------|--------|-----------------|
| Rich SVG characters (face, clothes) | High | Very High | 4 |
| Smooth camera (single zoompan pass) | Low | High | 1 |
| Piper TTS integration | Medium | High | 2 |
| Multi-character frames | Medium | High | 2 |
| Layered backgrounds | Medium | Medium | 2 |
| Color grading per scene | Low | Medium | 1 |
| Lip-sync approximation | Medium | Low-Medium | 2 |

Start with highest impact per effort: smooth camera + color grading → rich characters → piper TTS → multi-character → layered backgrounds → lip sync.
