from pathlib import Path
from typing import Any

import pytest

from video_convert_tools.basics import find_video_files, get_language, get_video_info


@pytest.fixture
def video_stream_hevc() -> dict[str, Any]:
    return {
        "index": 0,
        "codec_name": "hevc",
        "codec_type": "video",
        "tags": {"language": "eng"},
    }


@pytest.fixture
def video_stream_h264() -> dict[str, Any]:
    return {
        "index": 0,
        "codec_name": "h264",
        "codec_type": "video",
        "tags": {"language": "eng"},
    }


@pytest.fixture
def audio_stream_no_language() -> dict[str, Any]:
    return {
        "index": 1,
        "codec_name": "aac",
        "codec_type": "audio",
        "tags": {},
    }


@pytest.fixture
def audio_stream_eng() -> dict[str, Any]:
    return {
        "index": 1,
        "codec_name": "aac",
        "codec_type": "audio",
        "tags": {"language": "eng"},
    }


@pytest.fixture
def h264_file() -> Path:
    return Path(__file__).parent / "data" / "h264_mp3_en_esp.mp4"


@pytest.fixture
def hevc_file() -> Path:
    return Path(__file__).parent / "data" / "hevc_aac_de.mp4"


@pytest.fixture
def ffv1_file() -> Path:
    return Path(__file__).parent / "data" / "ffv1_pcm.avi"


@pytest.fixture
def stream_hevc_eng(
    video_stream_hevc: dict[str, Any], audio_stream_eng: dict[str, Any]
) -> dict[str, Any]:
    return {"streams": [video_stream_hevc, audio_stream_eng]}


@pytest.fixture
def stream_h264_noaudio(
    video_stream_h264: dict[str, Any], audio_stream_no_language: dict[str, Any]
) -> dict[str, Any]:
    return {"streams": [video_stream_h264, audio_stream_no_language]}


def test_get_language(
    audio_stream_eng: dict[str, Any], audio_stream_no_language: dict[str, Any]
) -> None:
    assert get_language(audio_stream_eng) == "eng"
    assert get_language(audio_stream_no_language) == "unk"


def test_get_video_info(hevc_file: Path, h264_file: Path, ffv1_file: Path) -> None:
    hevc_info = get_video_info(hevc_file)
    assert hevc_info is not None
    assert hevc_info.codec == "hevc"
    assert hevc_info.width == 1280
    assert hevc_info.height == 720

    h264_info = get_video_info(h264_file)
    assert h264_info is not None
    assert h264_info.codec == "h264"
    assert h264_info.width == 1280
    assert h264_info.height == 720

    ffv1_info = get_video_info(ffv1_file)
    assert ffv1_info is not None
    assert ffv1_info.codec == "ffv1"
    assert ffv1_info.width == 640
    assert ffv1_info.height == 480


def test_find_video_files() -> None:
    test_folder = Path(__file__).parent / "data"
    video_files = find_video_files(test_folder)
    expected_files = {
        test_folder / "h264_mp3_en_esp.mp4",
        test_folder / "hevc_aac_de.mp4",
        test_folder / "ffv1_pcm.avi",
    }
    assert set(video_files) == expected_files


@pytest.mark.parametrize(
    ("video_file", "expected_season"),
    [
        ("Show.S01E01.mkv", "S01"),
        ("Show_S02_E05.mp4", "S02"),
        ("Show-3x10.avi", "S03"),
        ("ShowSeason04Episode12.mkv", "S04"),
        ("Show.E10.S05.mkv", "S05"),
        ("RandomVideo.mkv", "Unknown"),
    ],
)
def test_season_info(video_file: str, expected_season: str) -> None:
    from video_convert_tools.basics import find_season_info

    season = find_season_info(Path(video_file))
    assert season == expected_season
