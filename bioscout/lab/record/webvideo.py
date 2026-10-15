"""Make recorded videos playable in a web browser.

OpenCV's stock 'mp4v' fourcc writes MPEG-4 Part 2, which Chrome, Edge, Firefox
and Safari all refuse to decode - so BioScout Web's "Analyse a video file"
answered "Could not read that video" for everything the screen recorder saved.
Browsers want H.264 (avc1) with yuv420p pixels, and the moov atom at the front.

`make_web_playable` rewrites a file in place to that format. It prefers ffmpeg
(on PATH, or the binary bundled with `pip install imageio-ffmpeg`) and falls
back to OpenCV's own H.264 writer (Media Foundation on Windows).
"""

import os
import shutil
import subprocess
from pathlib import Path

import cv2

_H264_TAGS = {'avc1', 'h264', 'x264'}


def ffmpeg_exe():
    """Path to an ffmpeg binary, or None."""
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def fourcc_of(path):
    """Lower-case fourcc of the first video stream ('' if unreadable)."""
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return ''
        v = int(cap.get(cv2.CAP_PROP_FOURCC))
    finally:
        cap.release()
    return ''.join(chr((v >> (8 * i)) & 0xFF) for i in range(4)).strip('\x00').lower()


def is_web_playable(path):
    return fourcc_of(path) in _H264_TAGS


def _ffmpeg_h264(exe, src, dst, wav_path=None):
    cmd = [exe, '-y', '-i', str(src)]
    if wav_path is not None:
        cmd += ['-i', str(wav_path)]
    cmd += ['-map', '0:v:0']
    if wav_path is not None:
        cmd += ['-map', '1:a:0', '-c:a', 'aac', '-shortest']
    else:
        cmd += ['-map', '0:a?', '-c:a', 'aac']
    cmd += ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
            # yuv420p needs even sides; pad (never rescale) an odd capture area
            '-vf', 'pad=ceil(iw/2)*2:ceil(ih/2)*2',
            '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dst)]
    try:
        kw = {}
        if os.name == 'nt':
            kw['creationflags'] = 0x08000000  # CREATE_NO_WINDOW
        r = subprocess.run(cmd, capture_output=True, timeout=1800, **kw)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and Path(dst).exists() and Path(dst).stat().st_size > 0


def _opencv_h264(src, dst):
    """Re-encode through OpenCV's H.264 writer (video only). True on success."""
    cap = cv2.VideoCapture(str(src))
    if not cap.isOpened():
        return False
    fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    W, H = w + (w % 2), h + (h % 2)
    out = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*'avc1'), fps, (W, H))
    if not out.isOpened():
        cap.release()
        out.release()
        return False
    n = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if (W, H) != (w, h):
                frame = cv2.copyMakeBorder(frame, 0, H - h, 0, W - w,
                                           cv2.BORDER_CONSTANT, value=(0, 0, 0))
            out.write(frame)
            n += 1
    finally:
        cap.release()
        out.release()
    return n > 0 and is_web_playable(dst)


def make_web_playable(path, wav_path=None):
    """Rewrite `path` in place as browser-playable H.264, muxing `wav_path` in
    if given. Returns True when the file at `path` is H.264 afterwards (audio
    is only muxed on the ffmpeg route)."""
    path = Path(path)
    if wav_path is None and is_web_playable(path):
        return True
    tmp = path.with_name(path.stem + '.h264tmp.mp4')
    ok = False
    exe = ffmpeg_exe()
    if exe:
        ok = _ffmpeg_h264(exe, path, tmp, wav_path)
    if not ok and wav_path is None:
        ok = _opencv_h264(path, tmp)
    if ok:
        os.replace(tmp, path)
    else:
        try:
            tmp.unlink()
        except OSError:
            pass
    return ok


NOT_PLAYABLE_HINT = ("MPEG-4 video: browsers can't play it. "
                     "pip install imageio-ffmpeg, then re-save")
