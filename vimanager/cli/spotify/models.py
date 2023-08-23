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
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from .matching import artists_fixup, main_artist, other_artists, slugify, title

if TYPE_CHECKING:
    from typing_extensions import Self


@dataclass(frozen=True, eq=True)
class YouTube:
    name: str
    url: str
    video_id: str
    author: str
    artists: Tuple[str, ...]
    album: Optional[str]
    duration: float
    song: bool

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> Optional[Self]:
        if not data:
            return
        video_id = data.get("videoId")
        artists = data.get("artists")
        if not video_id or not artists:
            return
        duration = data.get("duration")
        if not duration:
            duration = 0
        else:
            try:
                mapped_increments = zip([1, 60, 3600], reversed(duration.split(":")))
                seconds = sum(multiplier * int(time) for multiplier, time in mapped_increments)
                duration = seconds

            except (ValueError, TypeError, AttributeError):
                duration = 0

        return cls(
            name=data["title"],
            url=f"https://music.youtube.com/watch?v={video_id}",
            video_id=video_id,
            author=data["artists"][0]["name"],
            artists=tuple(map(lambda x: x["name"], data["artists"])),
            album=(data.get("album") or {}).get("name"),
            duration=duration,
            song=data.get("resultType") == "song",
        )


@dataclass(frozen=True, eq=True)
class Spotify:
    name: str
    artist: str
    artists: List[str]
    album: Optional[str]
    duration: str
    duration_ms: int
    song_id: str
    url: str
    isrc: Optional[str]
    cover_url: Optional[str]

    def compare(self, youtube_track: YouTube) -> float:
        spotify_words = slugify(self.name).split("-")
        youtube_words = slugify(youtube_track.name).replace("-", "")

        if not any(word in youtube_words for word in spotify_words if word != ""):
            return 0

        main_artist_match = main_artist(self, youtube_track)
        other_artists_match = other_artists(self, youtube_track)
        artist_match = artists_fixup(self, youtube_track, main_artist_match + other_artists_match)
        name_match = title(self, youtube_track)
        if youtube_track.album and self.album:
            album_match = fuzz.ratio(slugify(self.album), slugify(youtube_track.album))
        else:
            album_match = 0
        if youtube_track.duration > self.duration_ms:
            time_match = 100 - (youtube_track.duration - self.duration_ms // 1000)
        else:
            time_match = 100 - (self.duration_ms // 1000 - youtube_track.duration)
        time_match = min(time_match, 100)

        if name_match <= 60:
            return 0
        if artist_match < 70:
            return 0

        average_match = (artist_match + name_match) / 2
        if youtube_track.song and youtube_track.album and album_match <= 80:
            average_match = (average_match + album_match) / 2

        if time_match < 50 and average_match < 75:
            return 0

        return min(average_match, 100)

    @classmethod
    def from_data(cls, data: Dict[str, Any]) -> Optional[Self]:
        meta = data.get("track", {})
        track_id = meta.get("id")
        if not meta or not track_id:
            return
        duration_ms = meta["duration_ms"]
        minutes, seconds = divmod(duration_ms // 1000, 60)
        duration_text = f"{minutes}:{seconds}"

        album_meta = meta.get("album", {})
        images = album_meta.get("images")
        if images:
            cover_url = max(album_meta["images"], key=lambda i: i["width"] * i["height"])["url"]
        else:
            cover_url = None
        artists = [artist["name"] for artist in meta.get("artists", [])]

        return cls(
            name=meta["name"],
            artist=artists[0],
            artists=artists,
            album=album_meta.get("name"),
            duration=duration_text,
            duration_ms=duration_ms,
            song_id=track_id,
            url=meta["external_urls"]["spotify"],
            isrc=meta.get("external_ids", {}).get("isrc"),
            cover_url=cover_url,
        )
