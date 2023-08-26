# -*- coding: utf-8 -*-

"""
The MIT License (MIT)

Copyright (c) 2023-present Lee-matod

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
import pathlib
import subprocess
from typing import List

FFMPEG_FORMATS = {
    "mp3": ["-codec:a", "libmp3lame"],
    "flac": ["-codec:a", "flac", "-sample_fmt", "s16"],
    "ogg": ["-codec:a", "libvorbis"],
    "opus": ["-codec:a", "libopus"],
    "m4a": ["-codec:a", "aac"],
    "wav": ["-codec:a", "pcm_s16le"],
}


def convert(in_file: pathlib.Path, out_file: pathlib.Path, output_format: str):
    arguments: List[str] = [
        "-nostdin",
        "-y",
        "-i",
        str(in_file.resolve()),
        "-movflags",
        "+faststart",
        "-v",
        "debug",
        "-progress",
        "-",
        "-nostats",
    ]
    file_format = str(in_file.suffix).split(".")[1]
    if output_format == "opus" and file_format != "webm":
        arguments.extend(["-c:a", "libopus"])
    else:
        if (output_format == "opus" and file_format == "webm") or (output_format == "m4a" and file_format == "m4a"):
            arguments.extend(["-vn", "-c:a", "copy"])
        else:
            arguments.extend(FFMPEG_FORMATS[output_format])
    arguments.append(str(out_file.resolve()))

    with subprocess.Popen(
        ["ffmpeg", *arguments],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=False,
    ) as process:
        out_buffer: List[str] = []
        while True:
            if process.stdout is None:
                continue

            out_line = process.stdout.readline().decode("utf-8", errors="replace").strip()

            if out_line == "" and process.poll() is not None:
                break

            out_buffer.append(out_line.strip())

        return process.returncode == 0


def to_ms(*, hour: int = 0, min: int = 0, sec: int = 0, ms: int = 0) -> float:
    return (hour * 60 * 60 * 1000) + (min * 60 * 1000) + (sec * 1000) + ms
