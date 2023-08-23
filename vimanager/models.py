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

import sqlite3
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from typing_extensions import Self


class Song:
    def __init__(
        self, song_id: str, /, title: str, artist: str, *, duration: str, thumbnail: str, liked: bool = False
    ) -> None:
        self.id: str = song_id
        self.title: str = title
        self.artist: str = artist
        self.duration: str = duration
        self.thumbnail_url: str = thumbnail
        self.liked: bool = liked

    def __repr__(self) -> str:
        return f"<Song id={self.id!r} title={self.title!r} artist={self.artist!r}>"

    def __str__(self) -> str:
        return f"{self.artist} - {self.title}"

    @classmethod
    def from_database(cls, data: Tuple[str, str, str, str, str, Optional[int], str]) -> Self:
        song_id, title, artist, duration, thumbnail, liked_at, _ = data
        return cls(song_id, title, artist, duration=duration, thumbnail=thumbnail, liked=bool(liked_at))


class Playlist:
    def __init__(self, playlist_id: int, /, name: str, *, connection: Optional[sqlite3.Connection] = None) -> None:
        self.id: int = playlist_id
        self.name: str = name

        self._tracks: List[Song] = []

        if connection is not None:
            self._update(connection)

    def __repr__(self) -> str:
        return f"<Playlist id={self.id!r} name={self.name!r} tracks={len(self._tracks)}>"

    def _update(self, connection: sqlite3.Connection, /) -> None:
        cursor = connection.cursor()
        try:
            tracks = dict(
                cursor.execute("SELECT songId, position FROM SongPlaylistMap WHERE playlistId=?", (self.id,)).fetchall()
            )
            build = ", ".join("?" for _ in tracks)
            song_data = cursor.execute(f"SELECT * FROM Song WHERE id IN ({build})", list(tracks.keys())).fetchall()
            for data in sorted(song_data, key=lambda x: tracks[x[0]]):
                self._tracks.append(Song.from_database(data))
        finally:
            cursor.close()

    @property
    def songs(self) -> Tuple[Song]:
        return tuple(self._tracks)
