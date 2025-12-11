import shutil
import time
from pathlib import Path
from typing import Annotated

import humanize
import typer
from rich.progress import track

from video_convert_tools.basics import (
    FFMPEGConfig,
    convert_video,
    find_video_files,
    get_video_info,
)
from video_convert_tools.logging import logger

ACCEPTABLE_CODECS_DEFAULT = ("hevc",)
# Minimum duration difference in seconds to consider a conversion failed
MIN_DURATION_DIFFERENCE = 5.0


def _filter_files_with_acceptable_codecs(
    video_files: list[Path], acceptable_codecs: list[str]
) -> list[Path]:
    """Filter list of video files to only those not in acceptable codecs.

    Args:
        video_files (list[Path]): List of video file paths.
        acceptable_codecs (tuple[str, ...]): Tuple of acceptable video codecs.

    Returns:
        list[Path]: List of video file paths that are not in acceptable codecs.
    """
    convertable_files = []
    for video_file in track(video_files, description="Scanning video files"):
        video_info = get_video_info(video_file)
        if video_info is None:
            logger.warning(f"Skipping file {video_file} due to probe error")
            continue
        logger.info(
            f"Video file: {video_file}, Width: {video_info.width}, "
            f"Height: {video_info.height}, Codec: {video_info.codec}, "
            f"Duration: {humanize.precisedelta(video_info.duration, format='%.0f')}s"
        )
        if video_info.codec not in acceptable_codecs:
            convertable_files.append(video_file)
    return convertable_files


def main(
    source_folder: Annotated[
        Path, typer.Option(help="Source folder containing video files")
    ],
    duration_tolerance: Annotated[
        float, typer.Option(help="Duration tolerance for video conversion")
    ] = 0.05,
    dry_run: Annotated[
        bool, typer.Option(help="Perform a dry run without making changes")
    ] = False,
    maximum_width: Annotated[
        int | None,
        typer.Option(help="Maximum width for the converted videos"),
    ] = None,
    preset: Annotated[
        str, typer.Option(help="FFMPEG preset for the conversion")
    ] = "p5",
    cq: Annotated[int, typer.Option(help="Constant quality for the conversion")] = 30,
    audio_language: Annotated[
        list[str] | None,
        typer.Option(help="Preferred audio language for the conversion"),
    ] = None,
    subtitle_language: Annotated[
        list[str] | None,
        typer.Option(help="Preferred subtitle language for the conversion"),
    ] = None,
    acceptable_codecs: Annotated[
        list[str] | None,
        typer.Option(help="Acceptable video codecs for the conversion"),
    ] = None,
    video_codec: Annotated[
        str, typer.Option(help="Target video codec for the conversion")
    ] = "hevc_nvenc",
    check_only: Annotated[
        bool, typer.Option(help="Only check for files to convert, do not convert")
    ] = False,
    subtitle_like_audio: Annotated[
        bool, typer.Option(help="Treat subtitle streams like audio streams")
    ] = False,
) -> None:
    subtitle_language = audio_language if subtitle_like_audio else subtitle_language
    ffmpeg_config = FFMPEGConfig(
        video_codec=video_codec,
        video_config={
            "preset": preset,
            "cq": str(cq),
            "rc": "vbr",
            "rc_lookahead": "15",
        },
        audio_languages=audio_language,
        subtitle_languages=subtitle_language,
        maximum_width=maximum_width,
    )
    logger.info(f"Using FFMPEG config: {ffmpeg_config}")

    video_files = find_video_files(source_folder)
    logger.info(f"Found {len(video_files)} video files in {source_folder}")

    acceptable_codecs = acceptable_codecs or list(ACCEPTABLE_CODECS_DEFAULT)
    convertable_files = _filter_files_with_acceptable_codecs(
        video_files, acceptable_codecs
    )

    logger.info(f"Found {len(convertable_files)} files to convert")

    if check_only:
        return

    temp_file = Path(f"temp_{int(time.time())}.mkv")
    for video_file in track(convertable_files, description="Converting video files"):
        source_video_info = get_video_info(video_file)
        logger.info(f"Converting file {video_file} with info {source_video_info}")
        if source_video_info is None:
            logger.warning(f"Skipping file {video_file} due to probe error")
            continue
        convert_video(
            video_file=video_file,
            output_file=temp_file,
            ffmpeg_config=ffmpeg_config,
            video_info=source_video_info,
            dry_run=dry_run,
        )
        if dry_run:
            logger.info(f"Dry run enabled, skipping verification for {video_file}")
            continue

        target_video_info = get_video_info(temp_file)
        if target_video_info is None:
            logger.error(f"Conversion failed for file {video_file}, temp file missing")
            continue
        logger.info(f"Converted file info: {target_video_info}")
        if (
            (
                duration_difference := abs(
                    target_video_info.duration - source_video_info.duration
                )
            )
            > duration_tolerance * source_video_info.duration
            and duration_difference > MIN_DURATION_DIFFERENCE
        ):
            logger.error(
                f"Conversion failed for file {video_file}, duration mismatch of more than "
                f"{duration_tolerance * 100:.0f}%: {duration_difference:.2f}s with source "
                f"duration {source_video_info.duration:.2f}s and target duration "
                f"{target_video_info.duration:.2f}s"
            )
            continue

        if video_file.suffix.lower() != ".mkv":
            video_file.rename(video_file.with_suffix(".mkv"))
        logger.info(f"Converted file to {target_video_info}")
        shutil.move(temp_file, video_file.with_suffix(".mkv"))
        logger.info(f"Replaced original file with converted file for {video_file}")

    temp_file.unlink(missing_ok=True)
    logger.info("Conversion completed")


def main_cli() -> None:
    typer.run(main)


if __name__ == "__main__":
    main_cli()
