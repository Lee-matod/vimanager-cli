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
import base64
import pathlib
from typing import Any

import requests
from mutagen._file import File  # type: ignore
from mutagen.flac import Picture
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, TIT2, TPE1, WOAS
from mutagen.mp4 import MP4Cover
from mutagen.wave import WAVE

from vimanager.models import Song

__all__ = ("embed_metadata", "embed_cover", "embed_wav_file")

M4A_TAG_PRESET = {"artist": "\xa9ART", "title": "\xa9nam", "albumart": "covr"}
TAG_PRESET = {key: key for key in M4A_TAG_PRESET}


def embed_metadata(output_file: pathlib.Path, song: Song, id3_separator: str = "/") -> None:
    encoding = output_file.suffix[1:]

    if encoding == "wav":
        embed_wav_file(output_file, song)
        return

    tag_preset = TAG_PRESET if encoding != "m4a" else M4A_TAG_PRESET

    try:
        audio_file = File(str(output_file.resolve()), easy=encoding == "mp3")

        if audio_file is None:
            raise TypeError(f"Unrecognized file format for {output_file} from {song.id}")
    except Exception as exc:
        raise TypeError("Unable to load file.") from exc

    audio_file[tag_preset["artist"]] = song.artist
    audio_file[tag_preset["title"]] = song.title

    if encoding == "mp3":
        if id3_separator != "/":
            audio_file.save(v23_sep=id3_separator, v2_version=3)  # type: ignore
        else:
            audio_file.save(v2_version=3)  # type: ignore

        audio_file = ID3(str(output_file.resolve()))

        audio_file.add(WOAS(encoding=3, url=f"https://music.youtube.com/watch?v={song.id}"))  # type: ignore

    audio_file = embed_cover(audio_file, song, encoding)

    if encoding == "mp3":
        audio_file.save(v23_sep=id3_separator, v2_version=3)
    else:
        audio_file.save()


def embed_cover(audio_file: Any, song: Song, encoding: str) -> Any:
    if not song.thumbnail_url:
        return audio_file

    try:
        cover_data = requests.get(song.thumbnail_url, timeout=10).content
    except Exception:
        return audio_file

    if encoding in ["flac", "ogg", "opus"]:
        picture = Picture()
        picture.type = 3
        picture.desc = "Cover"
        picture.mime = "image/jpeg"
        picture.data = cover_data

        if encoding in ["ogg", "opus"]:
            image_data = picture.write()
            encoded_data = base64.b64encode(image_data)
            vcomment_value = encoded_data.decode("ascii")
            audio_file["metadata_block_picture"] = [vcomment_value]
        elif encoding == "flac":
            audio_file.add_picture(picture)
    elif encoding == "m4a":
        audio_file[M4A_TAG_PRESET["albumart"]] = [MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)]
    elif encoding == "mp3":
        audio_file["APIC"] = APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data)

    return audio_file


def embed_wav_file(output_file: pathlib.Path, song: Song) -> None:
    audio = WAVE(output_file)
    if audio.tags:
        audio.tags.clear()
    audio.add_tags()

    audio.tags.add(TIT2(encoding=3, text=song.title))  # type: ignore
    audio.tags.add(TPE1(encoding=3, text=song.artist))  # type: ignore
    audio.tags.add(WOAS(encoding=3, text=f"https://music.youtube.com/watch?v={song.id}"))  # type: ignore

    if song.thumbnail_url:
        try:
            cover_data = requests.get(song.thumbnail_url, timeout=10).content
            audio.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover_data))  # type: ignore
        except Exception:
            pass

    audio.save()  # type: ignore
