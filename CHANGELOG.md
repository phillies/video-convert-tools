# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.1]

### Added

`convert_replace`
- Command line argument `subtitle-like-audio` for using the same languages for subtitles as defined for audio
- Command line argument `check-only` which only checks which files would be converted

### Changed

- Bugfix for duration not found, file not found, and duration mismatch. Now minimum difference needs to be 5 sec to be counted as different.

## [0.1.0]
Initial version

### Added

- `convert_replace` to re-encode and replace files
- `convert_sort` to re-encode and sort files based on episode information in the filename
