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
import sqlite3
from typing import List, Optional, Tuple

import click
from colorama import Back, Fore, Style

__all__ = ("find_playlist", "get_connection")


def find_playlist(name: Optional[str], /, cursor: sqlite3.Cursor) -> Tuple[int, str]:
    if name is not None:
        cursor.execute("SELECT id, name FROM Playlist WHERE name=?", (name,))
    else:
        cursor.execute("SELECT id, name FROM Playlist")
    matching_playlists: List[Tuple[int, str]] = cursor.fetchall()
    if not matching_playlists:
        raise click.ClickException("Playlist not found")
    if len(matching_playlists) == 1:
        return matching_playlists[0]
    fmt = (name or "") and " with the same name"
    click.echo(f"{Style.BRIGHT}{Fore.WHITE}Found {len(matching_playlists)} playlists{fmt}.")
    click.echo("\n".join(f"{Fore.BLACK}{i}. {Fore.CYAN}{n}" for i, n in matching_playlists))
    response = int(
        click.prompt(
            f"{Back.GREEN}Select the index of the playlist",
            type=click.Choice(tuple(map(lambda x: str(x[0]), matching_playlists))),
            show_choices=False,
        )
    )
    return response, [x[1] for x in matching_playlists if x[0] == response][0]


def get_connection(db: str, /) -> sqlite3.Connection:
    if db[-3:] != ".db":
        raise click.FileError(db, "not a valid backup database")
    try:
        conn = sqlite3.connect(db)
    except Exception as exc:
        raise click.FileError(db, str(exc)) from exc
    return conn
