#!/usr/bin/env python3
"""Turn one lesson day's content into a spoken MP3 with edge-tts.

Examples:
    python scripts/make_audio.py --task english --date 2026-11-19
    python scripts/make_audio.py --task english --date 2026-11-19 --dry-run
    python scripts/make_audio.py --task english --prune

The task renderer supplies the spoken script as ``(lang, text)`` segments, so
English is read by an English voice and Chinese explanations by a Chinese one.
Only lesson days get audio; review days return nothing to read.

Audio is written to the task's ``audio/`` directory and is not committed to
git (see .gitignore). The workflow keeps the last few days through
actions/cache, and ``--prune`` drops anything older than ``audio.retention_days``.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
import time
from datetime import date as date_cls
from datetime import datetime, timedelta
from pathlib import Path

import common

DEFAULT_VOICE_EN = "en-US-AriaNeural"
DEFAULT_VOICE_ZH = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "-5%"
DEFAULT_RETENTION_DAYS = 7
BYTES_PER_SECOND_48KBPS = 6000


def _audio_config(config: dict) -> dict:
    return config.get("audio") or {}


def _to_date(value: str) -> date_cls:
    return datetime.strptime(value, "%Y-%m-%d").date()


def group_segments(segments: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Merge consecutive segments of the same language into one TTS request."""
    groups: list[tuple[str, str]] = []
    for lang, text in segments:
        spoken = " ".join(str(text or "").split())
        if not spoken:
            continue
        if groups and groups[-1][0] == lang:
            groups[-1] = (lang, f"{groups[-1][1]} {spoken}")
        else:
            groups.append((lang, spoken))
    return groups


def synthesize(
    text: str,
    voice: str,
    rate: str,
    out_path: Path,
    attempts: int = 4,
) -> None:
    """Render text to an MP3, retrying transient edge-tts failures."""

    async def _run() -> None:
        import edge_tts

        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        await communicate.save(str(out_path))

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            if out_path.exists():
                out_path.unlink()
            asyncio.run(_run())
            if out_path.is_file() and out_path.stat().st_size > 0:
                return
            raise RuntimeError("edge-tts 生成了空文件")
        except Exception as exc:  # noqa: BLE001 - retry boundary
            last_error = exc
            if attempt >= attempts:
                break
            # speech.platform.bing.com 偶尔会连接重置，退避久一点再试。
            delay = 3.0 * (2 ** (attempt - 1))
            print(
                f"语音合成失败（第 {attempt}/{attempts} 次）：{exc}；{delay:g}s 后重试",
                file=sys.stderr,
            )
            time.sleep(delay)
    raise RuntimeError(f"语音合成失败（已重试 {attempts} 次）：{last_error}") from last_error


def synthesize_segments(
    groups: list[tuple[str, str]],
    config: dict,
    out_path: Path,
) -> None:
    """Synthesize each group with its language's voice and concatenate them."""
    audio = _audio_config(config)
    voices = {
        "en": str(audio.get("voice_en", DEFAULT_VOICE_EN)),
        "zh": str(audio.get("voice_zh", DEFAULT_VOICE_ZH)),
    }
    rate = str(audio.get("rate", DEFAULT_RATE))

    with tempfile.TemporaryDirectory(prefix="learning-hub-audio-") as temp_dir:
        chunks = []
        for index, (lang, text) in enumerate(groups, start=1):
            chunk = Path(temp_dir) / f"{index:02d}.mp3"
            synthesize(text, voices.get(lang, voices["en"]), rate, chunk)
            chunks.append(chunk)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as merged:
            for chunk in chunks:
                merged.write(chunk.read_bytes())


def prune_audio(directory: Path, keep_days: int, today: date_cls) -> list[str]:
    """Delete MP3s dated more than ``keep_days`` before ``today``."""
    if keep_days <= 0 or not directory.is_dir():
        return []
    cutoff = today - timedelta(days=keep_days)
    removed = []
    for path in sorted(directory.glob("*.mp3")):
        if not common.DATE_RE.match(path.stem):
            continue
        try:
            seen = _to_date(path.stem)
        except ValueError:
            continue
        if seen < cutoff:
            path.unlink()
            removed.append(path.name)
    return removed


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(common.ROOT))
    except ValueError:
        return str(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成一天讲解内容的音频。")
    parser.add_argument("--task", default="", help="任务名，例如 english（默认）")
    parser.add_argument("--date", help="日期 YYYY-MM-DD；默认按 config 时区取今天")
    parser.add_argument("--force", action="store_true", help="即使已存在也重新生成")
    parser.add_argument("--dry-run", action="store_true", help="只打印朗读稿，不合成")
    parser.add_argument("--prune", action="store_true", help="只清理过期音频，不合成")
    parser.add_argument("--no-prune", action="store_true", help="合成后不清理过期音频")
    parser.add_argument("--text-out", default="", help="可选：把朗读稿写入文件，便于检查")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        task = common.normalize_task(args.task)
        config = common.load_config(task)
        date_text = common.resolve_date(args.date, config)
        today = _to_date(date_text)
        directory = common.audio_dir(task, config)
        audio = _audio_config(config)
        keep_days = int(audio.get("retention_days", DEFAULT_RETENTION_DAYS))

        removed = prune_audio(directory, keep_days, today)
        if removed:
            print(f"已清理 {len(removed)} 个过期音频：{', '.join(removed)}")

        if args.prune:
            return 0

        if not common.audio_enabled(config):
            print("音频未开启（config.yml 的 audio.enabled），跳过。")
            return 0

        content = common.load_content(task, date_text, config)
        if common.content_mode(content) == "review":
            print(f"{date_text} 是复习日，暂时不生成音频。")
            return 0

        target = directory / f"{date_text}.mp3"
        if target.is_file() and not args.force and not args.dry_run:
            print(f"音频已存在，跳过生成：{_display_path(target)}")
            return 0

        renderer = common.load_renderer(task)
        build_segments = getattr(renderer, "content_to_audio_segments", None)
        if build_segments is None:
            raise ValueError(f"任务的 render.py 没有 content_to_audio_segments：{task}")

        name = str(config.get("name") or config.get("site_title") or "每日英语")
        groups = group_segments(build_segments(content, name))
        if not groups:
            print(f"{date_text} 没有可朗读的内容，跳过。", file=sys.stderr)
            return 1

        script = "\n".join(f"[{lang}] {text}" for lang, text in groups)
        char_count = len("".join(text for _, text in groups))
        print(f"日期：{date_text}｜段落：{len(groups)}｜字数：{char_count}")
        if args.text_out:
            script_path = Path(args.text_out).expanduser()
            if not script_path.is_absolute():
                script_path = Path.cwd() / script_path
            script_path.parent.mkdir(parents=True, exist_ok=True)
            script_path.write_text(script + "\n", encoding="utf-8")
            print(f"朗读稿：{script_path}")

        if args.dry_run:
            print(script)
            print("dry-run：未生成音频。")
            return 0

        synthesize_segments(groups, config, target)
        size = target.stat().st_size
        print(
            f"音频：{_display_path(target)}"
            f"（{size / 1024:.0f} KB，约 {size / BYTES_PER_SECOND_48KBPS / 60:.1f} 分钟）"
        )
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
