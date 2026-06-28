from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

from agno.agent import Agent

from holodeck.agents.base import AgentOutput, ReviewResult, StageType, ValidationResult
from holodeck.observability import observe

if TYPE_CHECKING:
    from agno.models.base import Model

    from holodeck.storage.media_storage import MediaStorage


def _has_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def _escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''").replace("%", "\\%")


def build_drawtext_filters(
    subtitle_data: list[dict],
    frame_duration: float,
) -> str:
    filters = []
    for sd in subtitle_data:
        start = sd["frame_index"] * frame_duration
        n_frames = sd.get("frame_count", 1)
        end = (sd["frame_index"] + n_frames) * frame_duration
        text = _escape_drawtext(sd.get("dialogue_text", ""))
        filters.append(
            f"drawtext=text='{text}'"
            f":x=(w-text_w)/2:y=h-50"
            f":fontcolor=white:fontsize=24"
            f":box=1:boxcolor=black@0.5:boxborderw=5"
            f":enable='between(t,{start},{end})'"
        )
    return ",".join(filters)


def _group_by_scene(
    subtitle_data: list[dict],
    png_files: list[str],
) -> list[tuple[str, list[str], list[dict]]]:
    groups: dict[str, list[tuple[int, str]]] = {}
    for sd in subtitle_data:
        scene = sd.get("scene", "1") or "1"
        fi = sd["frame_index"]
        fc = sd.get("frame_count", 1)
        if scene not in groups:
            groups[scene] = []
        for offset in range(fc):
            idx = fi + offset
            if idx < len(png_files):
                groups[scene].append((idx, png_files[idx]))
    for scene in groups:
        seen: set[int] = set()
        unique: list[tuple[int, str]] = []
        for idx, png in groups[scene]:
            if idx not in seen:
                seen.add(idx)
                unique.append((idx, png))
        groups[scene] = unique

    sorted_items = sorted(groups.items(), key=lambda x: x[1][0][0])
    result: list[tuple[str, list[str], list[dict]]] = []
    for sid, entries in sorted_items:
        frame_indices = {e[0] for e in entries}
        scene_sd = [
            sd for sd in subtitle_data
            if any(sd["frame_index"] + offset in frame_indices
                   for offset in range(sd.get("frame_count", 1)))
        ]
        result.append((sid, [e[1] for e in entries], scene_sd))
    return result


def _build_xfade_filtergraph(
    durations: list[float],
    transition: str = "fadeblack",
    overlap: float = 1.0,
) -> tuple[str, str]:
    n = len(durations)
    label = "v0"
    if n < 2:
        return "", "[0:v]"
    offset = durations[0] - overlap
    parts = [f"[0:v][1:v]xfade=transition={transition}:duration={overlap}:offset={max(offset,0)},format=yuv420p[{label}]"]
    for i in range(2, n):
        prev_label = label
        label = f"v{i-1}"
        offset = sum(durations[:i]) - i * overlap
        parts.append(f"[{prev_label}][{i}:v]xfade=transition={transition}:duration={overlap}:offset={max(offset,0)},format=yuv420p[{label}]")
    return ";".join(parts), label


_COLOR_PRESETS: dict[str, str | None] = {
    "warm": "colorbalance=rs=.15:gs=.05:bs=-.1",
    "cool": "colorbalance=rs=-.1:gs=-.1:bs=.2",
    "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131:0",
    "noir": "colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0",
    "vivid": "eq=saturation=1.5",
    "neutral": None,
}


def _resolve_color_filter(scene_moods: dict[str, str] | None, scene_id: str) -> str | None:
    mood = "noir"
    if scene_moods:
        mood = scene_moods.get(scene_id, "noir")
    return _COLOR_PRESETS.get(mood, _COLOR_PRESETS["noir"])


def _interpolate_zoom(
    start_zoom: float,
    end_zoom: float,
    total_frames: int,
) -> str:
    return f"1.03+{end_zoom - start_zoom}*on/{total_frames}"


def _build_camera_move_filter(
    camera_moves: list[dict] | None,
    scene_id: str,
    scene_frame_count: int,
    video_w: int = 1280,
    video_h: int = 720,
) -> str | None:
    if not camera_moves:
        return None
    for cm in camera_moves:
        if cm.get("scene") == scene_id:
            sz = cm.get("start_zoom", 1.0)
            ez = cm.get("end_zoom", 2.0)
            px_s = cm.get("pan_x_start", 0)
            px_e = cm.get("pan_x_end", 0)
            py_s = cm.get("pan_y_start", 0)
            py_e = cm.get("pan_y_end", 0)
            total = cm.get("duration_frames", scene_frame_count)
            zoom_expr = f"{sz}+({ez}-{sz})*on/{total}"
            pan_x_expr = f"{px_s}+({px_e}-{px_s})*on/{total}"
            pan_y_expr = f"{py_s}+({py_e}-{py_s})*on/{total}"
            return f"crop=iw/{zoom_expr}:ih/{zoom_expr}:{pan_x_expr}:{pan_y_expr},scale={video_w}:{video_h}"
    return None


class VideoAssemblerAgent:
    stage = StageType.ANIMATION
    _agent: Agent | None = None

    def __init__(
        self,
        model: Model | None = None,
        storage: MediaStorage | None = None,
    ) -> None:
        self._model = model
        self._storage = storage

    def _get_agent(self) -> Agent:
        if self._agent is None:
            kwargs: dict = dict(
                name="Video Assembler",
                role="You assemble frame sequences and audio into a video using FFmpeg zoompan, color grading, and drawtext filters. You produce the final playable .mp4.",
                instructions=[
                    "Concatenate frame images into a video at target framerate.",
                    "Apply single-pass smooth zoompan for continuous camera motion.",
                    "Apply per-scene color grading presets (warm, cool, sepia, noir, vivid).",
                    "Apply dolly/pan/tilt via crop+scale filter chain.",
                    "Burn subtitle text with drawtext filter.",
                    "Mix dialogue audio and synchronize with video.",
                    "Encode as H.264 .mp4.",
                ],
            )
            if self._model is not None:
                kwargs["model"] = self._model
            self._agent = Agent(**kwargs)
        return self._agent

    def validate_input(self, context: dict) -> ValidationResult:
        if not context.get("frame_svgs") and not context.get("dialogue_audio_urls"):
            return ValidationResult(valid=False, errors=["Frame SVGs or audio required"])
        return ValidationResult(valid=True)

    @observe(name="video_assembler.process", as_type="generation")
    def process(self, context: dict) -> AgentOutput:
        if not _has_ffmpeg():
            context["video_url"] = ""
            return AgentOutput(
                content="FFmpeg not found. Install ffmpeg to enable video assembly.",
                metadata={"stage": "animation", "agent": "video_assembler", "video_url": ""},
            )

        import os
        media_dir = os.path.join(context.get("output_dir", "./output"), "media", str(context.get("production_id", "unknown")))
        os.makedirs(media_dir, exist_ok=True)

        frame_svgs = context.get("frame_svgs", "")
        audio_urls = context.get("dialogue_audio_urls", [])
        subtitle_data = context.get("subtitle_data", [])
        scene_moods = context.get("scene_moods", {})
        color_grades: list[dict] = context.get("color_grades", [])
        camera_moves: list[dict] = context.get("camera_moves", [])
        preview = context.get("preview", False)
        prod_id = context.get("production_id", "unknown")
        ep_id = context.get("episode_id", "unknown")

        VIDEO_W = 640 if preview else 1280
        VIDEO_H = 360 if preview else 720

        ai_frames: dict[int, str] = context.get("ai_composited_frames", {})
        use_ai = bool(ai_frames)

        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            png_files = []

            if use_ai:
                sorted_idx = sorted(ai_frames.keys())
                for i, idx in enumerate(sorted_idx):
                    png_path = str(tmp_path / f"frame_{i:04d}.png")
                    try:
                        import shutil
                        shutil.copy2(ai_frames[idx], png_path)
                        png_files.append(png_path)
                    except OSError:
                        pass
            else:
                svg_frames = re.split(r"\n---NEXT FRAME---\n", frame_svgs)
                svg_frames = [s for s in svg_frames if "<svg" in s]
                if not svg_frames:
                    context["video_url"] = ""
                    return AgentOutput(content="No frames. No video generated.", metadata={"video_url": ""})

                max_frames = min(len(svg_frames), 50)
                for i, svg in enumerate(svg_frames[:max_frames]):
                    png_path = str(tmp_path / f"frame_{i:04d}.png")
                    proc = subprocess.run(
                        ["convert", "svg:-", "-background", "white", "-flatten", "-resize", f"{VIDEO_W}x{VIDEO_H}!", png_path],
                        input=svg.encode("utf-8"),
                        capture_output=True,
                    )
                    if proc.returncode == 0:
                        png_files.append(png_path)

            if not png_files:
                context["video_url"] = ""
                return AgentOutput(content="No frames available for assembly.", metadata={"video_url": ""})

            import json as _json
            total_audio_dur = 0.0
            for af in audio_urls:
                try:
                    r = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "json", af],
                        capture_output=True, text=True,
                    )
                    info = _json.loads(r.stdout)
                    dur = float(info["format"]["duration"])
                    total_audio_dur += dur
                except Exception:
                    pass
            total_audio_dur = max(total_audio_dur, 3.0)
            FPS = 24
            FRAME_DURATION = total_audio_dur / max(len(png_files), 1)
            d_per_input = int(FRAME_DURATION * FPS)

            scene_groups = _group_by_scene(subtitle_data, png_files)
            raw_video = str(tmp_path / "raw.mp4")
            color_grade_applied = "neutral"
            camera_motion_type = "none"
            smooth_zoom = True

            # Resolve color grading: color_grades override scene_moods
            resolved_grades: dict[str, str] = {}
            for cg in color_grades:
                resolved_grades[cg.get("scene", "")] = cg.get("mood", "noir")
            resolved_grades.update(scene_moods)

            def _render_scene_segment(
                scene_pngs_actual: list[str],
                scene_sd_actual: list[dict],
                scene_id_actual: str,
                out_path_actual: str,
            ) -> bool:
                nonlocal color_grade_applied, camera_motion_type
                n_frames = len(scene_pngs_actual)
                if n_frames == 0:
                    return False
                seg_dir = tmp_path / f"seg_{scene_id_actual}_frames"
                seg_dir.mkdir(exist_ok=True)
                for j, src in enumerate(scene_pngs_actual):
                    dst = str(seg_dir / f"frame_{j:04d}.png")
                    if src != dst:
                        os.symlink(src, dst)

                local_subtitle = []
                for j, sd in enumerate(scene_sd_actual):
                    local_sd = dict(sd)
                    local_sd["frame_index"] = j
                    local_subtitle.append(local_sd)

                # Step 1: Render raw 24fps video from scene frames (no zoompan)
                raw_seg = str(tmp_path / f"raw_{scene_id_actual}.mkv")
                raw_cmd = [
                    "ffmpeg", "-y",
                    "-framerate", str(FPS),
                    "-i", str(seg_dir / "frame_%04d.png"),
                    "-c:v", "rawvideo",
                    "-pix_fmt", "yuv420p",
                    "-s", f"{VIDEO_W}x{VIDEO_H}",
                    raw_seg,
                ]
                r_raw = subprocess.run(raw_cmd, capture_output=True)
                if r_raw.returncode != 0:
                    return False

                # Step 2: Apply SINGLE zoompan pass on raw video with continuous zoom
                scene_grade = _resolve_color_filter(resolved_grades, scene_id_actual)
                if scene_grade:
                    color_grade_applied = scene_grade.split("=")[0]
                else:
                    color_grade_applied = "neutral"

                zoom_expr = f"1.03+2.13*on/({n_frames}*{max(d_per_input,1)})"
                zoompan_filter = (
                    f"zoompan=z='{zoom_expr}'"
                    f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                    f":d={d_per_input}:s={VIDEO_W}x{VIDEO_H},fps={FPS}"
                )

                # Camera move filter (dolly/pan/tilt via crop+scale)
                cam_filter = _build_camera_move_filter(camera_moves, scene_id_actual, n_frames, VIDEO_W, VIDEO_H)
                if cam_filter:
                    camera_motion_type = "combined"
                else:
                    camera_motion_type = "zoom"

                filter_parts = [zoompan_filter]
                if cam_filter:
                    filter_parts.append(cam_filter)
                if scene_grade:
                    filter_parts.append(scene_grade)

                dt = build_drawtext_filters(local_subtitle, FRAME_DURATION)
                if dt:
                    filter_parts.append(dt)

                seg_filter = ",".join(filter_parts)
                seg_cmd = [
                    "ffmpeg", "-y",
                    "-i", raw_seg,
                    "-vf", seg_filter,
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    out_path_actual,
                ]
                r_seg = subprocess.run(seg_cmd, capture_output=True)
                return r_seg.returncode == 0

            if preview:
                FPS = 12
                total_audio_dur = min(total_audio_dur, 5.0)
                max_frames = min(len(png_files), 15)

            if len(scene_groups) > 1 and subtitle_data:
                segment_videos: list[str] = []
                segment_durations: list[float] = []
                for scene_id, scene_pngs, scene_sd in scene_groups:
                    seg_out = str(tmp_path / f"seg_{scene_id}.mp4")
                    seg_dur = len(scene_pngs) * FRAME_DURATION
                    segment_durations.append(seg_dur)
                    ok = _render_scene_segment(scene_pngs, scene_sd, scene_id, seg_out)
                    if ok:
                        segment_videos.append(seg_out)
                    else:
                        context["video_url"] = ""
                        err = (subprocess.run(
                            ["ffprobe", "-v", "error", raw_video], capture_output=True, text=True
                        ) if os.path.exists(raw_video) else None)
                        return AgentOutput(
                            content=f"Scene {scene_id} render failed.",
                            metadata={"video_url": ""},
                        )

                xfade_applied = False
                if len(segment_videos) > 1:
                    xfade_check = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
                    has_xfade = "xfade" in xfade_check.stdout
                    if has_xfade:
                        fg, final_label = _build_xfade_filtergraph(segment_durations, "fadeblack", 1.0)
                        seg_inputs = []
                        for sv in segment_videos:
                            seg_inputs.extend(["-i", sv])
                        xfade_cmd = [
                            "ffmpeg", "-y", *seg_inputs,
                            "-filter_complex", fg,
                            "-map", f"[{final_label}]",
                            "-c:v", "libx264",
                            "-preset", "ultrafast",
                            "-pix_fmt", "yuv420p",
                            raw_video,
                        ]
                        r_xfade = subprocess.run(xfade_cmd, capture_output=True)
                        if r_xfade.returncode == 0:
                            xfade_applied = True

                if not xfade_applied:
                    concat_list = tmp_path / "segments.txt"
                    concat_list.write_text("".join(f"file '{sv}'\n" for sv in segment_videos))
                    concat_cmd = [
                        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                        "-i", str(concat_list),
                        "-c", "copy", raw_video,
                    ]
                    r_concat = subprocess.run(concat_cmd, capture_output=True)
                    if r_concat.returncode != 0:
                        context["video_url"] = ""
                        err = r_concat.stderr.decode()[-1000:]
                        return AgentOutput(content=f"Segment concat failed: {err}", metadata={"video_url": ""})
            else:
                scene_id = "1"
                ok = _render_scene_segment(png_files, subtitle_data, scene_id, raw_video)
                if not ok:
                    context["video_url"] = ""
                    return AgentOutput(content="Scene render failed.", metadata={"video_url": ""})

            final_video_name = f"episode_{ep_id}.mp4" if ep_id != "unknown" else "final.mp4"
            final_video = os.path.join(media_dir, final_video_name)

            mixed_audio = context.get("mixed_audio_path")
            if mixed_audio and os.path.exists(mixed_audio):
                cmd2 = [
                    "ffmpeg", "-y",
                    "-i", raw_video,
                    "-i", mixed_audio,
                    "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "128k", "-shortest",
                    final_video,
                ]
                subprocess.run(cmd2, capture_output=True)
            else:
                local_audio = []
                for url in (audio_urls or []):
                    if os.path.exists(url):
                        local_audio.append(url)
                if local_audio:
                    inputs = ["-i", raw_video]
                    for a in local_audio:
                        inputs.extend(["-i", a])
                    audio_labels = "".join(f"[{i+1}:a]" for i in range(len(local_audio)))
                    concat_filter = f"{audio_labels}concat=n={len(local_audio)}:v=0:a=1[aout]"
                    cmd2 = [
                        "ffmpeg", "-y", *inputs,
                        "-filter_complex", concat_filter,
                        "-map", "0:v", "-map", "[aout]",
                        "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "128k", "-shortest",
                        final_video,
                    ]
                    subprocess.run(cmd2, capture_output=True)
                else:
                    import shutil
                    shutil.copy2(raw_video, final_video)

            video_url = ""
            if os.path.exists(final_video):
                video_url = final_video
                if self._storage:
                    with open(final_video, "rb") as f:
                        video_data = f.read()
                    import asyncio
                    video_url = asyncio.run(
                        self._storage.upload_media(str(prod_id), str(ep_id), "final", final_video_name, video_data)
                    )

        context["video_url"] = video_url
        subtitles_burned = bool(subtitle_data)
        scene_segments = len(scene_groups)
        try:
            xfade_applied = xfade_applied
        except NameError:
            xfade_applied = False
        return AgentOutput(
            content=f"Video assembled: {video_url}" if video_url else "Video assembled (no storage).",
            metadata={
                "stage": "animation",
                "agent": "video_assembler",
                "video_url": video_url,
                "subtitles_burned": subtitles_burned,
                "xfade_applied": xfade_applied,
                "scene_segments": scene_segments,
                "smooth_zoom": smooth_zoom,
                "color_grade_applied": color_grade_applied,
                "camera_motion_type": camera_motion_type,
                "enhancement_type": "ai_composited" if use_ai else "svg",
            },
        )

    @observe(name="video_assembler.review", as_type="generation")
    def review_output(self, output: AgentOutput) -> ReviewResult:
        vu = ""
        if output.metadata:
            vu = output.metadata.get("video_url", "")
        if not vu:
            return ReviewResult(approved=False, score=0, feedback="No video produced.")
        return ReviewResult(approved=True, score=85, feedback=f"Video ready: {vu}")
