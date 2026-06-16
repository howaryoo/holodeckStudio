from __future__ import annotations

import asyncio
import subprocess

DEFAULT_PITCH_MAP: dict[str, float] = {
    "male": -2.0,
    "female": 3.0,
    "neutral": 0.0,
}


def _semitone_factor(semitones: float) -> float:
    return 2.0 ** (semitones / 12.0)


def build_pitch_shift_cmd(
    audio_path: str,
    semitones: float,
    output_path: str,
) -> list[str]:
    factor = _semitone_factor(semitones)
    return _ffmpeg_cmd([
        "-i", audio_path,
        "-af", f"asetrate=44100*{factor},aresample=44100",
        output_path,
    ])


def _ffmpeg_cmd(args: list[str]) -> list[str]:
    return ["ffmpeg", "-y", *args]


def build_frame_concat_cmd(
    frame_files: list[str],
    output_path: str,
    fps: int = 24,
    bw: bool = True,
) -> tuple[list[str], bytes]:
    filter_parts = [f"[0:v]fps={fps}"]
    if bw:
        filter_parts.append("colorchannelmixer=.3:.4:.3:0:.3:.4:.3:0:.3:.4:.3:0")
    filter_chain = ",".join(filter_parts)
    concat_content = "\n".join(f"file '{f}'" for f in frame_files)
    args = _ffmpeg_cmd([
        "-f", "concat",
        "-safe", "0",
        "-i", "-",
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        output_path,
    ])
    return args, concat_content.encode("utf-8")


def build_audio_mix_cmd(
    video_path: str,
    audio_files: list[str],
    output_path: str,
) -> list[str]:
    if not audio_files:
        return _ffmpeg_cmd(["-i", video_path, "-c", "copy", output_path])
    inputs = ["-i", video_path]
    for af in audio_files:
        inputs.extend(["-i", af])
    audio_labels = "".join(f"[{i+1}:a]" for i in range(len(audio_files)))
    concat_filter = f"{audio_labels}concat=n={len(audio_files)}:v=0:a=1[aout]"
    return _ffmpeg_cmd([
        *inputs,
        "-filter_complex", concat_filter,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        output_path,
    ])


async def run_ffmpeg(cmd: list[str], stdin: bytes | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed (code {proc.returncode}): {stderr.decode()[:500]}")
    return stdout.decode()
