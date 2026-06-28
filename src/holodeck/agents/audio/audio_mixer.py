from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AudioMixer:
    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True, timeout=5,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("FFmpeg not found at %s. Audio mixing disabled.", self.ffmpeg_path)

    def _has_ffmpeg(self) -> bool:
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True, timeout=5,
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_duration(self, audio_path: str) -> float:
        try:
            result = subprocess.run(
                [self.ffmpeg_path.replace("ffmpeg", "ffprobe"),
                 "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
            return 0.0

    def mix_scene(
        self,
        dialogue_path: str,
        ambience_path: Optional[str] = None,
        sfx_paths: Optional[list[str]] = None,
        output_path: str = "",
        scene_duration: float = 0.0,
    ) -> Optional[str]:
        if not self._has_ffmpeg():
            logger.warning("FFmpeg unavailable. Returning dialogue path unmixed.")
            return dialogue_path

        if not output_path:
            output_path = dialogue_path.replace(".mp3", "_mixed.mp3")

        inputs = ["-i", dialogue_path]
        out_labels: list[str] = []
        filter_parts: list[str] = []
        stream_idx = 0

        out_labels.append("[d]")
        filter_parts.append("[0:a]volume=1.0[d]")

        if ambience_path and os.path.exists(ambience_path):
            inputs.extend(["-i", ambience_path])
            stream_idx += 1
            dur = self.get_duration(ambience_path)
            if dur < scene_duration * 0.9 and dur > 0:
                samples = int(scene_duration * 44100)
                filter_parts.append(f"[{stream_idx}:a]volume=0.25,aloop=loop=-1:size={samples}[a]")
            else:
                filter_parts.append(f"[{stream_idx}:a]volume=0.25,atrim=0:{scene_duration}[a]")
            out_labels.append("[a]")

        if sfx_paths:
            for i, sfx_path in enumerate(sfx_paths):
                if not os.path.exists(sfx_path):
                    continue
                inputs.extend(["-i", sfx_path])
                stream_idx += 1
                sfx_idx = f"s{i}"
                filter_parts.append(f"[{stream_idx}:a]volume=0.5[{sfx_idx}]")
                out_labels.append(f"[{sfx_idx}]")

        mix_inputs = len(out_labels)
        if mix_inputs == 1:
            result = subprocess.run(
                [self.ffmpeg_path, "-y", "-i", dialogue_path,
                 "-c", "copy", output_path],
                capture_output=True, timeout=30,
            )
            return output_path if result.returncode == 0 else None

        label_refs = "".join(out_labels)
        amix = f"{label_refs}amix=inputs={mix_inputs}:duration=first:dropout_transition=0[out]"
        full_filter = ";".join(filter_parts) + ";" + amix
        cmd = [
            self.ffmpeg_path, "-y", *inputs,
            "-filter_complex", full_filter,
            "-map", "[out]",
            "-t", str(scene_duration),
            output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                logger.warning("FFmpeg mix failed (code %d)", result.returncode)
                return None
            return output_path
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg mix timed out for scene")
            return None

    def concat_scenes(
        self,
        scene_paths: list[str],
        output_path: str,
    ) -> Optional[str]:
        if not scene_paths:
            return None
        if len(scene_paths) == 1:
            if scene_paths[0] != output_path:
                subprocess.run(
                    [self.ffmpeg_path, "-y", "-i", scene_paths[0],
                     "-c", "copy", output_path],
                    capture_output=True, timeout=30,
                )
            return output_path

        inputs = []
        for p in scene_paths:
            inputs.extend(["-i", p])
        concat_filter = f"concat=n={len(scene_paths)}:v=0:a=1[out]"
        cmd = [
            self.ffmpeg_path, "-y", *inputs,
            "-filter_complex", concat_filter,
            "-map", "[out]",
            output_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                logger.warning("FFmpeg concat failed (code %d): %s", result.returncode, result.stderr.decode()[:500])
                return None
            return output_path
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg concat timed out")
            return None
