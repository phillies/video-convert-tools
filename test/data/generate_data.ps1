# create a small SRT for the H264 file (PowerShell)
@"
1
00:00:00,000 --> 00:00:01,000
Línea 1
2
00:00:01,000 --> 00:00:02,000
Línea 2
"@ > subs.srt

# 1) HEVC (libx265) + AAC audio with language=de (2s, random video+audio)
ffmpeg -f lavfi -i "testsrc=duration=2:size=1280x720:rate=30" -f lavfi -i "anoisesrc=duration=2:sample_rate=44100" -c:v libx265 -preset fast -pix_fmt yuv420p -tag:v hvc1 -c:a aac -b:a 128k -metadata:s:a:0 language=de -t 2 -movflags +faststart hevc_aac_de.mp4

# 2) H.264 (libx264) + MP3 audio with language=en + separate subtitle track language=es (2s)
ffmpeg -f lavfi -i "testsrc=duration=2:size=1280x720:rate=30" -f lavfi -i "sine=frequency=440:duration=2" -i subs.srt -map 0:v -map 1:a -map 2 -c:v libx264 -preset fast -crf 23 -c:a libmp3lame -b:a 192k -c:s mov_text -metadata:s:a:0 language=en -metadata:s:s:0 language=es -t 2 -movflags +faststart h264_mp3_en_esp.mp4

# 3) FFV1 video in AVI + PCM audio (no language tag) (2s)
ffmpeg -f lavfi -i "testsrc=duration=2:size=640x480:rate=5" -f lavfi -i "anoisesrc=duration=2:sample_rate=11025" -c:v ffv1 -level 3 -slicecrc 1 -pix_fmt yuv420p -c:a pcm_s16le -t 2 ffv1_pcm.avi
