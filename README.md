# Video Convert Tools
Collection of tools and scripts to (batch) convert video files using ffmpeg and NVIDIA codec.

Requires `ffmpeg` to be installed and an NVIDIA GPU with nvenc codec enabled in ffmpeg.

`convert_replace` checks a given source folder for all video files which are not hevc/h265 encoded and re-encodes them. The source file will be renamed to `.mkv` and replaced after a successful reencoding. It's successfull if the total duration does not deviate more than `duration_tolerance=0.05` from the original file.

`convert_sort` converts all files in a given folder and stores them in a target folder. It checks for indication of seasons (`S1E17`, `2x03`, ...) and creates `Sxx` subfolders.

For both tools you can define which audio and subtitle languages should be kept.

Check `convert_replace --help` and `convert_sort --help` for further information on the command line arguments.
