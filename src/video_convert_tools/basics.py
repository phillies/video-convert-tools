import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

import ffmpeg

if TYPE_CHECKING:
    from ffmpeg.dag.nodes import FilterableStream

from video_convert_tools.logging import logger

SUFFIXES = {".mkv", ".mp4", ".avi", ".mpg", ".mpeg", ".m4v", ".mov", ".wmv", ".flv"}


@dataclass
class FFMPEGConfig:
    """Configuration for ffmpeg video conversion.

    Attributes:
        video_codec (str): The video codec to use for conversion.
        video_config (dict[str, str]): Configuration options for the video codec.
        audio_codec (str): The audio codec to use for conversion. Defaults to "copy".
        audio_config (list[str]): Additional audio configuration options. Defaults to an empty list.
        subtitle_languages (list[str] | None): List of subtitle languages to include. If None, includes all subtitles.
        audio_languages (list[str] | None): List of audio languages to include. If None, includes all audio streams.
        maximum_width (int | None): Maximum width for the output video. If None, no resizing is applied.
    """

    video_codec: str
    video_config: dict[str, str]
    audio_codec: str = "copy"
    audio_config: list[str] = field(default_factory=list)
    subtitle_languages: list[str] | None = None
    audio_languages: list[str] | None = None
    maximum_width: int | None = None


@dataclass(frozen=True)
class VideoInfo:
    """Dataclass to hold video information.

    Attributes:
        video_file (Path): The path to the video file.
        width (int): The width of the video.
        height (int): The height of the video.
        codec (str): The codec of the video.
        audio_languages (tuple[str, ...]): Tuple of audio language codes in the video.
        subtitle_languages (tuple[str, ...]): Tuple of subtitle language codes in the video.
        duration (float): The duration of the video in seconds.
    """

    video_file: Path
    width: int
    height: int
    codec: str
    audio_languages: tuple[str, ...]
    subtitle_languages: tuple[str, ...]
    duration: float


def get_language(stream: dict[str, Any]) -> str:
    """Extract language from stream tags.

    Args:
        stream (dict[str, Any]): The ffprobe stream dictionary for an audio or subtitle stream.
    Returns:
        str: The language code if available, otherwise 'unk' (unknown).
    """
    if "tags" in stream and "language" in stream["tags"]:
        return str(stream["tags"]["language"])
    return "unk"


@cache
def get_video_info(video_file: Path) -> VideoInfo | None:
    """Get video information using ffprobe.

    Args:
        video_file (Path): The path to the video file.

    Returns:
        VideoInfo: A dataclass containing video information.
    """
    try:
        file_info = ffmpeg.probe(video_file)
    except ffmpeg.FFMpegExecuteError:
        logger.error(f"Error probing video file {video_file}.")
        return None

    video_streams = [
        stream for stream in file_info["streams"] if stream["codec_type"] == "video"
    ]
    audio_streams = [
        stream for stream in file_info["streams"] if stream["codec_type"] == "audio"
    ]
    subtitle_streams = [
        stream for stream in file_info["streams"] if stream["codec_type"] == "subtitle"
    ]

    if not video_streams:
        logger.error(f"No video stream found in file {video_file}.")
        return None

    if len(video_streams) > 1:
        logger.warning(
            f"Multiple video streams found in file {video_file}, using the first one"
        )
    return VideoInfo(
        video_file=video_file,
        width=int(video_streams[0]["width"]),
        height=int(video_streams[0]["height"]),
        codec=video_streams[0]["codec_name"],
        audio_languages=tuple(get_language(stream) for stream in audio_streams),
        subtitle_languages=tuple(get_language(stream) for stream in subtitle_streams),
        duration=float(file_info["format"]["duration"]),
    )


def find_video_files(
    root_folder: str | Path, suffixes: set[str] | None = None
) -> list[Path]:
    """Find video files in the given root folder with specified suffixes.

    Args:
        root_folder (str): The root folder to search for video files.
        suffixes (set[str] | None): A set of file suffixes to include. If None, defaults to common video suffixes.

    Returns:
        list[Path]: A sorted list of Paths to the found video files.
    """
    root_path = Path(root_folder)
    suffixes = suffixes or SUFFIXES

    video_files = [file for file in root_path.rglob("*") if file.suffix in suffixes]
    return sorted(video_files)


@cache
def find_season_info(video_file: str | Path) -> str:
    """Extract season information from the video file name.

    Args:
        video_file (Path): The video file path.
    Returns:
        str: The season folder name, e.g., 'S01', or 'Unknown' if not found.
    """
    match = re.search(r"([Ss])?(\d{1,2}).?[EeXx](\d{1,2})", str(video_file))
    if match:
        season_number = int(match.group(2))
        season_folder = f"S{season_number:02d}"
    else:
        season_folder = "Unknown"
    return season_folder


def convert_video(
    video_file: Path,
    output_file: Path,
    ffmpeg_config: FFMPEGConfig,
    video_info: VideoInfo,
    dry_run: bool = False,
) -> None:
    """Convert a video file using the specified ffmpeg configuration.

    Args:
        video_file (Path): The path to the input video file.
        output_file (Path): The path to the output video file.
        ffmpeg_config (FFMPEGConfig): The ffmpeg configuration to use for conversion.
        video_info (VideoInfo): The video information of the input file.
        dry_run (bool): If True, only log the ffmpeg command without executing it.
    """
    input_stream = ffmpeg.input(video_file)

    mux_streams: list[FilterableStream] = []

    # Video stream handling
    video_stream = input_stream.video_stream(index=0)
    if ffmpeg_config.maximum_width and video_info.width > ffmpeg_config.maximum_width:
        logger.info(
            f"Rescaling video from width {video_info.width} to {ffmpeg_config.maximum_width}"
        )
        video_stream = video_stream.scale(w=ffmpeg_config.maximum_width, h=-2)
    mux_streams.append(video_stream)

    # Audio stream handling
    if ffmpeg_config.audio_languages:
        logger.info("Selecting audio languages")
        # the audio stream mapping starts from 0 for the first audio stream
        for index, lang in enumerate(video_info.audio_languages):
            if lang in ffmpeg_config.audio_languages:
                logger.info(f"Selecting audio stream {index} with language {lang}")
                mux_streams.append(input_stream.audio_stream(index=index))
    elif len(video_info.audio_languages) > 0:
        logger.info("Selecting all audio streams")
        mux_streams.append(input_stream.audio)

    # Subtitle stream handling
    if ffmpeg_config.subtitle_languages:
        logger.info("Selecting subtitle languages")
        for index, lang in enumerate(video_info.subtitle_languages):
            if lang in ffmpeg_config.subtitle_languages:
                logger.info(f"Selecting subtitle stream {index} with language {lang}")
                mux_streams.append(input_stream.subtitle_stream(index=index))
    elif len(video_info.subtitle_languages) > 0:
        logger.info("Selecting all subtitle streams")
        mux_streams.append(input_stream.subtitle)

    # Encoding options
    if ffmpeg_config.video_codec not in dir(ffmpeg.codecs.encoders):
        logger.info(f"Available codecs: {dir(ffmpeg.codecs.encoders)}")
        raise ValueError(
            f"Video codec {ffmpeg_config.video_codec} not found in ffmpeg codecs"
        )
    encoder_options = getattr(ffmpeg.codecs.encoders, ffmpeg_config.video_codec)(
        **ffmpeg_config.video_config
    )

    command = ffmpeg.output(
        *mux_streams,
        filename=output_file,
        vcodec=ffmpeg_config.video_codec,
        acodec=ffmpeg_config.audio_codec,
        scodec="copy",
        encoder_options=encoder_options,
        extra_options={
            "disposition:s": "0",  # no subtitles by default
            "tag:v": "hvc1",  # apple compatibility
        },
    ).global_args(hide_banner=True, y=True)
    if dry_run:
        logger.info(f"Dry run, command: {command.compile_line()}")
    else:
        logger.debug(f"Running command: {command.compile_line()}")
        command.run(quiet=True)


def convert_videos(
    input_files: list[Path],
    output_files: list[Path],
    ffmpeg_config: FFMPEGConfig,
    dry_run: bool = False,
) -> None:
    """Convert multiple video files using the specified ffmpeg configuration.

    Args:
        input_files (list[Path]): A list of input video file paths.
        output_files (list[Path]): A list of output video file paths.
        ffmpeg_config (FFMPEGConfig): The ffmpeg configuration to use for conversion.
        dry_run (bool): If True, only log the ffmpeg commands without executing them.
    """
    for video_file, output_file in zip(input_files, output_files, strict=True):
        video_info = get_video_info(video_file)

        if video_info is None:
            logger.warning(f"Skipping file {video_file} due to probe error")
            continue

        convert_video(video_file, output_file, ffmpeg_config, video_info, dry_run)
