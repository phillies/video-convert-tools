from pathlib import Path
from typing import Annotated

import typer
from rich.progress import track

from video_convert_tools.basics import (
    FFMPEGConfig,
    convert_videos,
    find_season_info,
    find_video_files,
    get_video_info,
)
from video_convert_tools.logging import logger


def main(
    source_folder: Annotated[
        str, typer.Option(help="Source folder containing video files")
    ],
    target_folder: Annotated[
        str, typer.Option(help="Target folder for converted videos")
    ],
    cq: Annotated[int, typer.Option(help="Quality parameter for video encoding")] = 30,
    preset: Annotated[str, typer.Option(help="Preset for video encoding")] = "p5",
    dry_run: Annotated[
        bool,
        typer.Option(help="Perform a dry run without executing ffmpeg"),
    ] = False,
    resume: Annotated[
        bool, typer.Option(help="Resume conversion, i.e. do not replace existing files")
    ] = False,
    suffixes: Annotated[
        str | None,
        typer.Option(help="File suffixes to include, comma-separated w/o blanks"),
    ] = None,
    audio_languages: Annotated[
        list[str] | None, typer.Option(help="Audio languages to include")
    ] = None,
    subtitle_languages: Annotated[
        list[str] | None,
        typer.Option(
            help="Subtitle languages to include, if not set, use audio languages"
        ),
    ] = None,
    keep_folder: Annotated[
        bool,
        typer.Option(
            help="Keep the folder structure or sort them based on file name in season folders, default false"
        ),
    ] = False,
    maximum_width: Annotated[
        int | None,
        typer.Option(help="Rescale video to that width if set, default None"),
    ] = None,
    reencode: Annotated[
        bool, typer.Option(help="Re-encode video if already in HEVC format")
    ] = False,
) -> None:
    suffix_set = {f".{s}" for s in suffixes.split(",")} if suffixes else None
    video_files = find_video_files(source_folder, suffixes=suffix_set)

    logger.info(f"Found video {len(video_files)} files")

    logger.info(
        f"Running conversion, keeping languages {audio_languages if audio_languages else 'all'}"
    )

    ffmpeg_config = FFMPEGConfig(
        video_codec="hevc_nvenc",
        video_config={
            "preset": preset,
            "cq": str(cq),
            "rc": "vbr",
            "rc_lookahead": "15",
        },
        audio_codec="copy",
        audio_config=[],
        subtitle_languages=subtitle_languages,
        audio_languages=audio_languages,
        maximum_width=maximum_width,
    )

    # map of input file to output file
    convert_map = {}

    for video_file in track(
        video_files, description="Converting videos", total=len(video_files)
    ):
        video_info = get_video_info(video_file)

        if video_info is None:
            logger.warning(f"Skipping file {video_file} due to probe error")
            continue

        if video_info.codec == ffmpeg_config.video_codec and not reencode:
            logger.info(
                f"Skipping {video_file} as it is already in {ffmpeg_config.video_codec} format"
            )
            continue

        output_file = target_folder / video_file.relative_to(source_folder)

        if not keep_folder:
            season_folder = find_season_info(video_file)

            output_file = Path(target_folder) / season_folder / video_file.name

        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file = output_file.with_stem(
            output_file.stem.replace("264", "265")
        ).with_suffix(".mkv")

        if resume and output_file.exists():
            logger.warning(f"Skipping {video_file} as {output_file} already exists")
            continue

        convert_map[video_file] = output_file

    convert_videos(
        list(convert_map.keys()),
        list(convert_map.values()),
        ffmpeg_config,
        dry_run=dry_run,
    )


def main_cli() -> None:
    typer.run(main)


if __name__ == "__main__":
    main_cli()
